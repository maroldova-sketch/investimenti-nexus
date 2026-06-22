"""iDoklad v3 klient — OAuth2 client_credentials.

Creds z configu (.env):
    IDOKLAD_CLIENT_ID, IDOKLAD_CLIENT_SECRET, IDOKLAD_SCOPE
Token endpoint a API base jsou rovněž v configu.

Token se cachuje v paměti do vypršení (minus 60s rezerva).
Pozn.: mapování polí faktur dle iDoklad v3 — drobné rozdíly podle verze API
lze doladit v `_map_invoice()`.
"""
import threading
import time
from typing import Any, Optional

import httpx

from backend.config import get_settings

settings = get_settings()
_lock = threading.Lock()
_token_cache: dict[str, Any] = {"access_token": None, "exp": 0.0}


class IDokladError(RuntimeError):
    pass


def _configured() -> bool:
    return bool(settings.idoklad_client_id and settings.idoklad_client_secret)


def get_access_token(force: bool = False) -> str:
    if not _configured():
        raise IDokladError("iDoklad creds chybí (IDOKLAD_CLIENT_ID / IDOKLAD_CLIENT_SECRET)")
    with _lock:
        now = time.time()
        if not force and _token_cache["access_token"] and _token_cache["exp"] > now + 60:
            return _token_cache["access_token"]
        resp = httpx.post(
            settings.idoklad_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.idoklad_client_id,
                "client_secret": settings.idoklad_client_secret,
                "scope": settings.idoklad_scope,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        if resp.status_code != 200:
            raise IDokladError(f"token HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        tok = data.get("access_token")
        if not tok:
            raise IDokladError("access_token chybí v odpovědi")
        _token_cache["access_token"] = tok
        _token_cache["exp"] = now + float(data.get("expires_in", 3600))
        return tok


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_access_token()}",
            "Accept": "application/json", "Content-Type": "application/json"}


def _get(path: str, params: Optional[dict] = None) -> dict:
    url = f"{settings.idoklad_api_base.rstrip('/')}/{path.lstrip('/')}"
    r = httpx.get(url, headers=_headers(), params=params or {}, timeout=20)
    if r.status_code == 401:  # token vypršel mezi tím
        get_access_token(force=True)
        r = httpx.get(url, headers=_headers(), params=params or {}, timeout=20)
    if r.status_code >= 400:
        raise IDokladError(f"GET {path} HTTP {r.status_code}: {r.text[:200]}")
    return r.json()


def _post(path: str, body: dict) -> dict:
    url = f"{settings.idoklad_api_base.rstrip('/')}/{path.lstrip('/')}"
    r = httpx.post(url, headers=_headers(), json=body, timeout=20)
    if r.status_code == 401:
        get_access_token(force=True)
        r = httpx.post(url, headers=_headers(), json=body, timeout=20)
    if r.status_code >= 400:
        raise IDokladError(f"POST {path} HTTP {r.status_code}: {r.text[:200]}")
    return r.json() if r.text else {}


def ping() -> bool:
    """Ověří, že creds získají token. True/raise."""
    get_access_token(force=True)
    return True


# ── faktury ────────────────────────────────────────────────────────────────
def list_received_invoices(page: int = 1, page_size: int = 50) -> list[dict]:
    data = _get("ReceivedInvoices", {"page": page, "pageSize": page_size})
    return data.get("Data", data if isinstance(data, list) else [])


def list_issued_invoices(page: int = 1, page_size: int = 50) -> list[dict]:
    data = _get("IssuedInvoices", {"page": page, "pageSize": page_size})
    return data.get("Data", data if isinstance(data, list) else [])


def get_received_invoice(invoice_id: int) -> dict:
    return _get(f"ReceivedInvoices/{invoice_id}")


def _map_invoice(raw: dict, source: str) -> dict:
    """iDoklad faktura → znormalizovaný dict pro Fortis."""
    return {
        "source_ref": str(raw.get("Id") or raw.get("id") or ""),
        "doc_number": raw.get("DocumentNumber") or raw.get("documentNumber"),
        "doc_date": (raw.get("DateOfIssue") or raw.get("dateOfIssue") or "")[:10] or None,
        "due_date": (raw.get("DateOfMaturity") or raw.get("dateOfMaturity") or "")[:10] or None,
        "amount_gross": raw.get("TotalWithVat") or raw.get("Price") or raw.get("totalWithVat"),
        "amount_net": raw.get("TotalWithoutVat") or raw.get("totalWithoutVat"),
        "amount_vat": raw.get("TotalVat") or raw.get("totalVat"),
        "currency": raw.get("CurrencyCode") or "CZK",
        "counterparty_name": (raw.get("PartnerContact") or {}).get("CompanyName")
                             or raw.get("PartnerName"),
        "counterparty_ico": (raw.get("PartnerContact") or {}).get("IdentificationNumber"),
        "source_system": "idoklad",
        "doc_type": source,   # "received" / "issued"
        "raw": raw,
    }


def fetch_normalized(kind: str = "received", pages: int = 1, page_size: int = 50) -> list[dict]:
    """Vrátí znormalizované faktury (received|issued) napříč `pages` stránkami."""
    out: list[dict] = []
    fetch = list_received_invoices if kind == "received" else list_issued_invoices
    for p in range(1, pages + 1):
        batch = fetch(page=p, page_size=page_size)
        if not batch:
            break
        out.extend(_map_invoice(x, kind) for x in batch)
    return out
