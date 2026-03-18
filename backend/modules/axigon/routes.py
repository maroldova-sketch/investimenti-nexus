"""Wave 3.2 — Axigon account + contacts + intake sources."""
import os
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import Entity
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from .models import ExternalAccount, ExternalContact, ExternalContactAssignment, IntakeSource

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(tags=["axigon"])


def _ctx(d: dict) -> dict:
    d.setdefault("now_date", date.today().isoformat())
    d.setdefault("active_section", "fleet")
    return d


def _account_warnings(account, contacts, assignments):
    """Derive operational warnings for the account overview."""
    warnings = []
    if account.registration_valid_to:
        try:
            exp = datetime.strptime(account.registration_valid_to, "%Y-%m-%d").date()
            days = (exp - date.today()).days
            if days < 0:
                warnings.append({"level": "error", "msg": f"Registrace vypršela {account.registration_valid_to}!"})
            elif days < 60:
                warnings.append({"level": "warn", "msg": f"Registrace vyprší za {days} dní ({account.registration_valid_to})"})
        except: pass

    areas = ["contracts", "fuel_cards", "billing"]
    for area in areas:
        primary = [a for a in assignments if a.area == area and a.is_primary]
        if not primary:
            warnings.append({"level": "warn", "msg": f"Chybí primární kontakt pro oblast: {area}"})

    # Check invoice contact
    has_invoice = any(c.send_invoices and c.is_active for c in contacts)
    if not has_invoice:
        warnings.append({"level": "warn", "msg": "Žádný aktivní kontakt pro zasílání faktur"})

    return warnings


# ── AXIGON OVERVIEW ────────────────────────────────────────────────────
@router.get("/fleet/axigon", response_class=HTMLResponse)
def axigon_overview(request: Request, db: Session = Depends(get_db),
                    cu: CurrentUser = Depends(get_current_user)):
    account = db.query(ExternalAccount).filter(
        ExternalAccount.provider_code == "axigon"
    ).first()
    contacts = db.query(ExternalContact).filter(
        ExternalContact.external_account_id == account.id if account else "never"
    ).all() if account else []
    assignments = db.query(ExternalContactAssignment).filter(
        ExternalContactAssignment.external_contact_id.in_(
            [c.id for c in contacts]
        )
    ).all() if contacts else []
    sources = db.query(IntakeSource).order_by(IntakeSource.source_type).all()
    warnings = _account_warnings(account, contacts, assignments) if account else [{"level": "warn", "msg": "Axigon účet není nastaven"}]

    return templates.TemplateResponse("pages/axigon/overview.html", _ctx({
        "request": request, "current_user": cu,
        "account": account, "contacts": contacts,
        "assignments": assignments, "sources": sources,
        "warnings": warnings,
    }))


# ── AXIGON CONTACTS ────────────────────────────────────────────────────
@router.get("/fleet/axigon/contacts", response_class=HTMLResponse)
def axigon_contacts(request: Request,
                    sort: str = "display_name", dir: str = "asc",
                    db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    account = db.query(ExternalAccount).filter(
        ExternalAccount.provider_code == "axigon"
    ).first()
    if not account:
        raise HTTPException(404, "Axigon account not found — run seed first")

    contacts = db.query(ExternalContact).filter(
        ExternalContact.external_account_id == account.id
    ).all()

    # Sorting
    reverse = dir == "desc"
    sort_key = {
        "display_name": lambda c: c.display_name.lower(),
        "contact_type": lambda c: c.contact_type,
        "email": lambda c: (c.email or "").lower(),
        "status": lambda c: str(c.is_active),
    }.get(sort, lambda c: c.display_name.lower())
    contacts.sort(key=sort_key, reverse=reverse)

    # Enrich with assignments
    all_asgn = db.query(ExternalContactAssignment).filter(
        ExternalContactAssignment.external_contact_id.in_([c.id for c in contacts])
    ).all()
    asgn_map = {}
    for a in all_asgn:
        asgn_map.setdefault(a.external_contact_id, []).append(a)

    enriched = [{"contact": c, "assignments": asgn_map.get(c.id, [])} for c in contacts]
    sources = db.query(IntakeSource).order_by(IntakeSource.display_name).all()

    return templates.TemplateResponse("pages/axigon/contacts.html", _ctx({
        "request": request, "current_user": cu,
        "account": account, "enriched": enriched, "sources": sources,
        "sort": sort, "dir": dir,
    }))


# ── CONTACT TOGGLE ACTIVE ──────────────────────────────────────────────
@router.post("/fleet/axigon/contacts/{contact_id}/toggle")
def toggle_contact(contact_id: str, db: Session = Depends(get_db),
                   cu: CurrentUser = Depends(get_current_user)):
    c = db.query(ExternalContact).filter(ExternalContact.id == contact_id).first()
    if not c: raise HTTPException(404)
    c.is_active = not c.is_active
    db.commit()
    audit(db, "TOGGLE", "external_contact", c.id, cu.id, cu.email,
          detail=f"is_active={c.is_active}")
    return RedirectResponse("/fleet/axigon/contacts", status_code=303)


# ── SET PRIMARY CONTACT FOR AREA ───────────────────────────────────────
@router.post("/fleet/axigon/contacts/{contact_id}/set-primary")
def set_primary(contact_id: str, area: str = Form(...),
                db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    # Demote existing primary for this area
    c = db.query(ExternalContact).filter(ExternalContact.id == contact_id).first()
    if not c: raise HTTPException(404)

    existing = db.query(ExternalContactAssignment).filter(
        ExternalContactAssignment.area == area,
        ExternalContactAssignment.is_primary == True,
    ).all()
    for a in existing:
        a.is_primary = False; a.priority = "secondary"

    # Find or create assignment
    asgn = db.query(ExternalContactAssignment).filter(
        ExternalContactAssignment.external_contact_id == contact_id,
        ExternalContactAssignment.area == area,
    ).first()
    if asgn:
        asgn.is_primary = True; asgn.priority = "primary"
    else:
        db.add(ExternalContactAssignment(
            external_contact_id=contact_id, area=area,
            priority="primary", is_primary=True
        ))
    db.commit()
    audit(db, "SET_PRIMARY", "external_contact_assignment", contact_id, cu.id, cu.email,
          detail=f"area={area}")
    return RedirectResponse("/fleet/axigon/contacts", status_code=303)
