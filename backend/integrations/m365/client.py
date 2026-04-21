"""Thin wrapper around Microsoft Graph API using httpx."""
from __future__ import annotations
import httpx
from .auth import get_access_token

GRAPH = "https://graph.microsoft.com/v1.0"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_access_token()}"}


# ── Profile ──────────────────────────────────────────────────────────────────
def me() -> dict:
    r = httpx.get(f"{GRAPH}/me", headers=_headers(), timeout=15)
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
        f"{GRAPH}/me/mailFolders/{folder}/messages",
        headers=_headers(), params=params, timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_message(message_id: str) -> dict:
    r = httpx.get(
        f"{GRAPH}/me/messages/{message_id}",
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
    r = httpx.post(f"{GRAPH}/me/sendMail", headers=_headers(), json=payload, timeout=15)
    r.raise_for_status()


def search_messages(query: str, top: int = 20) -> dict:
    params = {
        "$search": f'"{query}"',
        "$top": top,
        "$select": "id,subject,from,receivedDateTime,bodyPreview",
    }
    r = httpx.get(f"{GRAPH}/me/messages", headers=_headers(), params=params, timeout=15)
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
    r = httpx.get(f"{GRAPH}/me/calendarView", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def get_event(event_id: str) -> dict:
    r = httpx.get(f"{GRAPH}/me/events/{event_id}", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


# ── Contacts ─────────────────────────────────────────────────────────────────
def list_contacts(top: int = 100) -> dict:
    params = {
        "$top": top,
        "$select": "id,displayName,emailAddresses,businessPhones,companyName,jobTitle",
        "$orderby": "displayName",
    }
    r = httpx.get(f"{GRAPH}/me/contacts", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ── Files (OneDrive / SharePoint) ────────────────────────────────────────────
def list_drive_root(top: int = 50) -> dict:
    params = {"$top": top, "$select": "id,name,size,lastModifiedDateTime,webUrl,folder,file"}
    r = httpx.get(f"{GRAPH}/me/drive/root/children", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()
