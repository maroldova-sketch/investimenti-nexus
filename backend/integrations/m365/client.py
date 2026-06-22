"""Thin wrapper around Microsoft Graph API using httpx.

Dva režimy (config M365_AUTH_MODE):
  - "delegated"  → token z refresh tokenu, kořen /me  (chování beze změny)
  - "app"        → client_credentials token, kořen /users/{M365_MAILBOX}
                   (umožní číst/posílat z konkrétní/sdílené schránky, např.
                    produkce@zamek-citoliby.cz)
"""
from __future__ import annotations
import httpx
from backend.config import get_settings
from .auth import get_access_token, get_app_token

GRAPH = "https://graph.microsoft.com/v1.0"


def _app_mode() -> bool:
    return get_settings().m365_auth_mode.lower() == "app"


def _token() -> str:
    return get_app_token() if _app_mode() else get_access_token()


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


def _root() -> str:
    """Kořen Graph cesty pro aktivní schránku."""
    s = get_settings()
    if _app_mode():
        if not s.m365_mailbox:
            raise RuntimeError("M365_AUTH_MODE=app vyžaduje nastavený M365_MAILBOX")
        return f"{GRAPH}/users/{s.m365_mailbox}"
    return f"{GRAPH}/me"


def active_mailbox() -> str:
    """Adresa schránky, se kterou se reálně pracuje (pro diagnostiku)."""
    s = get_settings()
    return s.m365_mailbox if _app_mode() else "(delegated /me)"


# ── Profile ──────────────────────────────────────────────────────────────────
def me() -> dict:
    r = httpx.get(_root(), headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


# ── Mail ─────────────────────────────────────────────────────────────────────
def list_messages(folder: str = "inbox", top: int = 20, skip: int = 0) -> dict:
    params = {
        "$top": top,
        "$skip": skip,
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview,hasAttachments",
    }
    r = httpx.get(
        f"{_root()}/mailFolders/{folder}/messages",
        headers=_headers(), params=params, timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_message(message_id: str) -> dict:
    r = httpx.get(
        f"{_root()}/messages/{message_id}",
        headers=_headers(),
        params={"$select": "id,subject,from,toRecipients,receivedDateTime,body,hasAttachments"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def send_mail(to: str | list[str], subject: str, body_html: str, save_to_sent: bool = True) -> None:
    if isinstance(to, str):
        to = [to]
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": a}} for a in to],
        },
        "saveToSentItems": save_to_sent,
    }
    r = httpx.post(f"{_root()}/sendMail", headers=_headers(), json=payload, timeout=15)
    r.raise_for_status()


def search_messages(query: str, top: int = 20) -> dict:
    params = {
        "$search": f'"{query}"',
        "$top": top,
        "$select": "id,subject,from,receivedDateTime,bodyPreview",
    }
    r = httpx.get(f"{_root()}/messages", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ── Calendar ─────────────────────────────────────────────────────────────────
def list_events(start: str, end: str, top: int = 50) -> dict:
    """List calendar events in a time range (ISO 8601 datetimes)."""
    params = {
        "startDateTime": start,
        "endDateTime": end,
        "$top": top,
        "$orderby": "start/dateTime",
        "$select": "id,subject,start,end,location,organizer,isAllDay,isCancelled",
    }
    r = httpx.get(f"{_root()}/calendarView", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def get_event(event_id: str) -> dict:
    r = httpx.get(f"{_root()}/events/{event_id}", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


# ── Contacts ─────────────────────────────────────────────────────────────────
def list_contacts(top: int = 100) -> dict:
    params = {
        "$top": top,
        "$select": "id,displayName,emailAddresses,businessPhones,companyName,jobTitle",
        "$orderby": "displayName",
    }
    r = httpx.get(f"{_root()}/contacts", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ── Files (OneDrive / SharePoint) ────────────────────────────────────────────
def list_drive_root(top: int = 50) -> dict:
    params = {"$top": top, "$select": "id,name,size,lastModifiedDateTime,webUrl,folder,file"}
    r = httpx.get(f"{_root()}/drive/root/children", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()
