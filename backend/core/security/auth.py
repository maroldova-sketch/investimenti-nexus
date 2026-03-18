import hashlib, os, hmac
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import UserAccount, RoleAssignment, NexusRole
from backend.config import get_settings

settings = get_settings()

PBKDF2_ITERATIONS = 260000
PBKDF2_ALGO = "sha256"

def hash_password(plain: str) -> str:
    salt = os.urandom(32).hex()
    dk = hashlib.pbkdf2_hmac(PBKDF2_ALGO, plain.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2:{salt}:{dk.hex()}"

def verify_password(plain: str, stored: str) -> bool:
    try:
        if stored.startswith("pbkdf2:"):
            _, salt, expected = stored.split(":", 2)
            dk = hashlib.pbkdf2_hmac(PBKDF2_ALGO, plain.encode(), salt.encode(), PBKDF2_ITERATIONS)
            return hmac.compare_digest(dk.hex(), expected)
        # legacy SHA256 fallback (migration period)
        salt, h = stored.split(":", 1)
        return hmac.compare_digest(
            hashlib.sha256(f"{salt}{plain}".encode()).hexdigest(), h
        )
    except Exception:
        return False

def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

class CurrentUser:
    def __init__(self, user: UserAccount, roles: list):
        self.id = user.id
        self.person_id = user.person_id
        self.email = user.email
        self.person = user.person
        self.roles = roles
        self.role = roles[0] if roles else NexusRole.READONLY
    def has_role(self, *roles) -> bool:
        return any(r in self.roles for r in roles)
    def is_admin_or_owner(self) -> bool:
        return self.has_role("owner", "admin")

def get_token(request: Request) -> Optional[str]:
    t = request.cookies.get("nexus_token")
    if not t:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            t = auth[7:]
    return t

def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    token = get_token(request)
    if not token:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    user = db.query(UserAccount).filter(
        UserAccount.id == user_id, UserAccount.is_active == True
    ).first()
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    roles = [r.role for r in db.query(RoleAssignment).filter(
        RoleAssignment.person_id == user.person_id
    ).all()]
    return CurrentUser(user, roles)
