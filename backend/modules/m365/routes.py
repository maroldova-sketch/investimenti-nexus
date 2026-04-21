"""M365 routes — mail inbox, send, calendar, contacts, files."""
import os
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.core.security.auth import get_current_user, CurrentUser
from backend.integrations.m365 import client as m365

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(prefix="/m365", tags=["m365"])


def _ctx(d: dict) -> dict:
    d.setdefault("now_date", date.today().isoformat())
    d.setdefault("active_section", "m365")
    return d


# ── Mail inbox ───────────────────────────────────────────────────────────────
@router.get("/mail", response_class=HTMLResponse)
def mail_inbox(request: Request, page: int = Query(0, ge=0),
               cu: CurrentUser = Depends(get_current_user)):
    per_page = 20
    data = m365.list_messages(top=per_page, skip=page * per_page)
    messages = data.get("value", [])
    return templates.TemplateResponse("pages/m365/mail.html", _ctx({
        "request": request, "current_user": cu,
        "messages": messages, "page": page,
        "has_next": "@odata.nextLink" in data,
    }))


@router.get("/mail/{message_id}", response_class=HTMLResponse)
def mail_detail(message_id: str, request: Request,
                cu: CurrentUser = Depends(get_current_user)):
    msg = m365.get_message(message_id)
    return templates.TemplateResponse("pages/m365/mail_detail.html", _ctx({
        "request": request, "current_user": cu, "msg": msg,
    }))


@router.get("/mail/search", response_class=HTMLResponse)
def mail_search(request: Request, q: str = Query(""),
                cu: CurrentUser = Depends(get_current_user)):
    messages = []
    if q:
        data = m365.search_messages(q)
        messages = data.get("value", [])
    return templates.TemplateResponse("pages/m365/mail.html", _ctx({
        "request": request, "current_user": cu,
        "messages": messages, "page": 0, "has_next": False, "search_query": q,
    }))


# ── Send mail ────────────────────────────────────────────────────────────────
@router.get("/mail/compose", response_class=HTMLResponse)
def mail_compose(request: Request, cu: CurrentUser = Depends(get_current_user)):
    return templates.TemplateResponse("pages/m365/mail_compose.html", _ctx({
        "request": request, "current_user": cu,
    }))


@router.post("/mail/send")
def mail_send(to: str = Form(...), subject: str = Form(...), body: str = Form(...),
              cu: CurrentUser = Depends(get_current_user)):
    recipients = [a.strip() for a in to.split(",") if a.strip()]
    m365.send_mail(recipients, subject, body)
    return RedirectResponse("/m365/mail", status_code=303)


# ── Calendar ─────────────────────────────────────────────────────────────────
@router.get("/calendar", response_class=HTMLResponse)
def calendar_view(request: Request,
                  start: str = Query(None), end: str = Query(None),
                  cu: CurrentUser = Depends(get_current_user)):
    today = date.today()
    if not start:
        start = today.isoformat() + "T00:00:00"
    if not end:
        end = (today + timedelta(days=14)).isoformat() + "T23:59:59"
    data = m365.list_events(start, end)
    events = data.get("value", [])
    return templates.TemplateResponse("pages/m365/calendar.html", _ctx({
        "request": request, "current_user": cu,
        "events": events, "start": start[:10], "end": end[:10],
    }))


# ── Contacts ─────────────────────────────────────────────────────────────────
@router.get("/contacts", response_class=HTMLResponse)
def contacts_list(request: Request, cu: CurrentUser = Depends(get_current_user)):
    data = m365.list_contacts()
    contacts = data.get("value", [])
    return templates.TemplateResponse("pages/m365/contacts.html", _ctx({
        "request": request, "current_user": cu, "contacts": contacts,
    }))


# ── Files ────────────────────────────────────────────────────────────────────
@router.get("/files", response_class=HTMLResponse)
def files_list(request: Request, cu: CurrentUser = Depends(get_current_user)):
    data = m365.list_drive_root()
    items = data.get("value", [])
    return templates.TemplateResponse("pages/m365/files.html", _ctx({
        "request": request, "current_user": cu, "items": items,
    }))


# ── Service manifest (for Elias discovery) ───────────────────────────────────
@router.get("/api/capabilities")
def api_capabilities():
    """Machine-readable manifest of available M365 operations."""
    return {
        "service": "nexus.m365",
        "base_url": "http://192.168.1.43:8000/m365",
        "account": "j.caka@vzc.cz",
        "capabilities": [
            {"id": "mail.list",     "method": "GET",  "path": "/api/mail",          "params": ["top", "skip"],    "description": "List inbox messages"},
            {"id": "mail.search",   "method": "GET",  "path": "/api/mail",          "params": ["$search"],        "description": "Search messages by query"},
            {"id": "mail.send",     "method": "POST", "path": "/api/mail/send",     "params": ["to", "subject", "body"], "description": "Send email via Outlook"},
            {"id": "calendar.list", "method": "GET",  "path": "/api/calendar",      "params": ["start", "end"],   "description": "List calendar events in date range (ISO 8601)"},
            {"id": "contacts.list", "method": "GET",  "path": "/api/contacts",      "params": [],                 "description": "List Outlook contacts"},
            {"id": "files.list",    "method": "GET",  "path": "/api/files",         "params": [],                 "description": "List OneDrive root files"},
            {"id": "profile",       "method": "GET",  "path": "/api/me",            "params": [],                 "description": "Get M365 user profile"},
        ],
    }


# ── JSON API (for AJAX / Elias) ──────────────────────────────────────────────
@router.get("/api/me")
def api_me(cu: CurrentUser = Depends(get_current_user)):
    return m365.me()


@router.get("/api/mail")
def api_mail(top: int = Query(20), skip: int = Query(0),
             cu: CurrentUser = Depends(get_current_user)):
    return m365.list_messages(top=top, skip=skip)


@router.get("/api/calendar")
def api_calendar(start: str = Query(...), end: str = Query(...),
                 cu: CurrentUser = Depends(get_current_user)):
    return m365.list_events(start, end)


@router.post("/api/mail/send")
def api_send_mail(to: str = Form(...), subject: str = Form(...), body: str = Form(...),
                  cu: CurrentUser = Depends(get_current_user)):
    recipients = [a.strip() for a in to.split(",") if a.strip()]
    m365.send_mail(recipients, subject, body)
    return {"status": "sent", "to": recipients}


@router.get("/api/contacts")
def api_contacts(cu: CurrentUser = Depends(get_current_user)):
    return m365.list_contacts()


@router.get("/api/files")
def api_files(cu: CurrentUser = Depends(get_current_user)):
    return m365.list_drive_root()
