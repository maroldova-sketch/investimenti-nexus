"""Strojová autentizace pro Elias / MCP / n8n.

Dvě nezávislé vrstvy:
  1) API-key (ServiceToken)  → pro JSON API /api/v1/*
  2) HMAC podpis             → pro /webhooks/* (sdílený WEBHOOK_SECRET)

Použití v routách:
    @router.get("/api/v1/fleet/vehicles")
    def _(tok: ServiceToken = Depends(require_scope("fleet:read"))): ...
"""
import hashlib
import hmac
import os
import secrets as _secrets
from datetime import datetime
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.core.models.base import get_db
from backend.modules.mcp_api.models import ServiceToken

settings = get_settings()

PBKDF2_ITER = 200_000
KEY_PREFIX = "nxs"


# ── token tvorba / hash ─────────────────────────────────────────────────────
def hash_secret(secret: str) -> str:
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt.encode(), PBKDF2_ITER)
    return f"pbkdf2:{salt}:{dk.hex()}"


def verify_secret(secret: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split(":", 2)
        dk = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt.encode(), PBKDF2_ITER)
        return hmac.compare_digest(dk.hex(), expected)
    except Exception:
        return False


def generate_token() -> tuple[str, str, str]:
    """Vrátí (full_token, key_id, secret). Plný token se ukáže uživateli JEN jednou."""
    key_id = _secrets.token_hex(6)            # 12 hex znaků
    secret = _secrets.token_urlsafe(32)
    full = f"{KEY_PREFIX}_{key_id}_{secret}"
    return full, key_id, secret


def _parse_token(raw: str) -> Optional[tuple[str, str]]:
    """nxs_<key_id>_<secret> → (key_id, secret)."""
    if not raw or not raw.startswith(KEY_PREFIX + "_"):
        return None
    parts = raw.split("_", 2)
    if len(parts) != 3:
        return None
    _, key_id, secret = parts
    if not key_id or not secret:
        return None
    return key_id, secret


def _extract_raw(request: Request) -> Optional[str]:
    raw = request.headers.get("X-API-Key")
    if raw:
        return raw.strip()
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


# ── FastAPI dependency ──────────────────────────────────────────────────────
def get_service_token(request: Request, db: Session = Depends(get_db)) -> ServiceToken:
    raw = _extract_raw(request)
    parsed = _parse_token(raw) if raw else None
    if not parsed:
        raise HTTPException(status_code=401, detail="Missing or malformed API key (X-API-Key / Bearer nxs_...)")
    key_id, secret = parsed
    tok = db.query(ServiceToken).filter(
        ServiceToken.key_id == key_id, ServiceToken.is_active == True  # noqa: E712
    ).first()
    if not tok or not verify_secret(secret, tok.hashed_secret):
        raise HTTPException(status_code=401, detail="Invalid API key")
    if tok.expires_at and tok.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key expired")
    tok.last_used_at = datetime.utcnow()
    db.commit()
    return tok


def require_scope(scope: str) -> Callable:
    """Dependency factory: ověří platný token + požadovaný scope."""
    def _dep(tok: ServiceToken = Depends(get_service_token)) -> ServiceToken:
        if not tok.allows(scope):
            raise HTTPException(status_code=403, detail=f"Token nemá scope '{scope}'")
        return tok
    return _dep


# ── webhook HMAC ────────────────────────────────────────────────────────────
async def verify_webhook_signature(request: Request) -> None:
    """Ověří `X-Nexus-Signature: sha256=<hex>` proti raw body.

    - GET/HEAD se přeskakují.
    - Pokud WEBHOOK_SECRET není nastaven → HMAC vypnuté (zpětná kompatibilita),
      ale chování je explicitní a dohledatelné.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    secret = settings.webhook_secret
    if not secret:
        return  # HMAC vypnuté – viz WEBHOOK_SECRET v .env
    sig = request.headers.get("X-Nexus-Signature", "")
    if sig.startswith("sha256="):
        sig = sig[7:]
    body = await request.body()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not sig or not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


# ── kombinovaná auth: přihlášený uživatel (cookie/JWT) NEBO service token ────
def require_human_or_service(request: Request, db: Session = Depends(get_db)) -> dict:
    """Projde, pokud je platná buď session cookie/Bearer JWT (člověk),
    nebo API-key service token (stroj). Jinak 403.

    Pro routy volané jak z UI (prohlížeč s cookie), tak strojově (n8n/Elias).
    """
    # 1) service token (X-API-Key / Bearer nxs_...)
    raw = _extract_raw(request)
    parsed = _parse_token(raw) if raw else None
    if parsed:
        key_id, secret = parsed
        tok = db.query(ServiceToken).filter(
            ServiceToken.key_id == key_id, ServiceToken.is_active == True  # noqa: E712
        ).first()
        if tok and verify_secret(secret, tok.hashed_secret):
            if not (tok.expires_at and tok.expires_at < datetime.utcnow()):
                tok.last_used_at = datetime.utcnow(); db.commit()
                return {"kind": "service", "name": tok.name}

    # 2) přihlášený uživatel (cookie nebo Bearer JWT)
    from backend.core.security.auth import decode_token
    from backend.core.models.kernel import UserAccount
    token = request.cookies.get("nexus_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and not auth[7:].startswith(KEY_PREFIX + "_"):
            token = auth[7:]
    if token:
        try:
            uid = decode_token(token).get("sub")
            user = db.query(UserAccount).filter(
                UserAccount.id == uid, UserAccount.is_active == True  # noqa: E712
            ).first()
            if user:
                return {"kind": "user", "email": user.email}
        except Exception:
            pass

    raise HTTPException(status_code=403, detail="Vyžaduje přihlášení nebo API klíč")
