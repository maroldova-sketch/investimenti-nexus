"""
Fleet completion routes — pro doplnění chybějících dat (❓) v insurance claims a fleet events.
"""
import os, uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.core.models.base import get_db
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from backend.modules.fortis.models import FortisDocument, FortisCostRecord

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(prefix="/fleet", tags=["fleet-completion"])


@router.get("/completion", response_class=HTMLResponse)
def completion_list(request: Request, db: Session = Depends(get_db),
                    cu: CurrentUser = Depends(get_current_user)):
    """Přehled všech záznamů s chybějícími daty."""
    pending_claims = db.execute(text("""
        SELECT ic.id, v.spz, v.make, v.model, ic.claim_date, ic.insurer_ref,
               ic.amount_claimed, ic.amount_settled, ic.status,
               substr(ic.description,1,100) as desc,
               e.code as entity_code
        FROM insurance_claim ic
        JOIN vehicle v ON v.id = ic.vehicle_id
        LEFT JOIN entity e ON e.id = COALESCE(ic.entity_id, v.entity_id)
        WHERE ic.status != 'settled' OR ic.amount_settled IS NULL
        ORDER BY ic.claim_date DESC
    """)).fetchall()

    pending_events = db.execute(text("""
        SELECT fe.id, v.spz, fe.event_type, fe.event_date,
               fe.cost_kc, substr(fe.description,1,80) as desc
        FROM fleet_event fe
        JOIN vehicle v ON v.id = fe.vehicle_id
        WHERE fe.description LIKE '%❓%'
           OR fe.cost_kc IS NULL
           OR fe.description LIKE '%?%'
        ORDER BY fe.event_date DESC
    """)).fetchall()

    okim_invoices = db.execute(text("""
        SELECT fe.id, v.spz, fe.event_date, fe.cost_kc, substr(fe.description,1,100) as desc
        FROM fleet_event fe JOIN vehicle v ON v.id=fe.vehicle_id
        WHERE fe.event_type = 'servis'
        ORDER BY fe.event_date DESC
    """)).fetchall()

    return templates.TemplateResponse("pages/fleet/completion.html", {
        "request": request, "current_user": cu,
        "active_section": "fleet",
        "pending_claims": pending_claims,
        "pending_events": pending_events,
        "okim_invoices": okim_invoices,
        "total_pending": len(pending_claims),
    })


@router.get("/completion/claim/{claim_id}", response_class=HTMLResponse)
def completion_claim_form(claim_id: str, request: Request,
                           db: Session = Depends(get_db),
                           cu: CurrentUser = Depends(get_current_user)):
    claim = db.execute(text("""
        SELECT ic.*, v.spz, v.make, v.model, e.code as entity_code
        FROM insurance_claim ic
        JOIN vehicle v ON v.id = ic.vehicle_id
        LEFT JOIN entity e ON e.id = COALESCE(ic.entity_id, v.entity_id)
        WHERE ic.id = :id
    """), {'id': claim_id}).fetchone()
    if not claim:
        return RedirectResponse("/fleet/completion")

    return templates.TemplateResponse("pages/fleet/completion_claim.html", {
        "request": request, "current_user": cu,
        "active_section": "fleet",
        "claim": claim,
    })


@router.post("/completion/claim/{claim_id}")
def completion_claim_save(
    claim_id: str,
    amount_settled: str = Form(""),
    spoluucast: str = Form(""),
    status: str = Form("pending"),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user),
):
    def _f(v):
        try: return float(v.replace(',', '.').replace(' ', '')) if v.strip() else None
        except: return None

    settled_val = _f(amount_settled)
    spolu_val = _f(spoluucast)
    now = datetime.now()

    updates = {'status': status, 'updated_at_placeholder': now}
    set_parts = ["status = :status"]

    if settled_val is not None:
        updates['settled'] = settled_val
        set_parts.append("amount_settled = :settled")
        if status == 'pending':
            status = 'settled'
            updates['status'] = 'settled'

    # Append notes to description
    if notes.strip():
        existing_desc = db.execute(text("SELECT description FROM insurance_claim WHERE id=:id"), {'id': claim_id}).scalar() or ''
        updates['description'] = existing_desc + f"\n[{now.strftime('%Y-%m-%d')}] {notes}"
        set_parts.append("description = :description")
        if spolu_val:
            updates['description'] += f" | spoluúčast: {spolu_val:,.0f} Kč"

    db.execute(text(f"UPDATE insurance_claim SET {', '.join(set_parts)} WHERE id = :id"),
               {**updates, 'id': claim_id})
    db.commit()

    # Sync to FORTIS if settled
    if settled_val:
        _sync_claim_to_fortis(db, claim_id, settled_val, cu, now)

    audit(db, "UPDATE", "insurance_claim", claim_id, cu.id, cu.email,
          detail=f"Doplněno: plnění={settled_val}, spoluúčast={spolu_val}")
    return RedirectResponse("/fleet/completion", status_code=303)


def _sync_claim_to_fortis(db, claim_id: str, settled: float, cu, now):
    """Update FORTIS document + add cost record if not exists."""
    # Update existing fortis_document
    db.execute(text("""
        UPDATE fortis_document SET status='approved', updated_at=:now
        WHERE nexus_ref_type='insurance_claim' AND nexus_ref_id=:id
    """), {'now': now, 'id': claim_id})

    # Add cost record if not exists
    existing = db.execute(text("""
        SELECT id FROM fortis_cost_record
        WHERE nexus_ref_type='insurance_claim' AND nexus_ref_id=:id
    """), {'id': claim_id}).fetchone()
    if not existing:
        claim = db.execute(text("SELECT * FROM insurance_claim WHERE id=:id"), {'id': claim_id}).fetchone()
        if claim:
            vehicle = db.execute(text("SELECT entity_id, id FROM vehicle WHERE id=:id"), {'id': claim[1]}).fetchone()
            eid = vehicle[0] if vehicle else None
            date_str = claim[4] or now.strftime('%Y-%m-%d')
            db.execute(text("""
                INSERT INTO fortis_cost_record
                (id,entity_id,cost_type,period_year,period_month,vehicle_id,amount,currency,unit,notes,nexus_ref_type,nexus_ref_id,created_at)
                VALUES (:id,:eid,'pojisteni',:py,:pm,:vid,:amt,'CZK','Kč',:notes,'insurance_claim',:nri,:now)
            """), {'id': str(uuid.uuid4()), 'eid': eid,
                   'py': int(date_str[:4]), 'pm': int(date_str[5:7]),
                   'vid': claim[1], 'amt': settled,
                   'notes': f"Plnění pojistka | ref {claim[6]}",
                   'nri': claim_id, 'now': now})
    db.commit()
