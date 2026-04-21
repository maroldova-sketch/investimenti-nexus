
# ── FORTIS push helper ────────────────────────────────────────────────────
import urllib.request, json as _json
FORTIS_URL = "http://localhost:8050"

def push_advance_to_fortis(case, person, year: int, month: int) -> dict:
    """Odešle schválenou zálohu/srážku do FORTIS. Vrátí výsledek API."""
    if not getattr(person, "fortis_doctor_uuid", None) and not getattr(person, "external_id", None):
        return {"status": "skip", "reason": "no fortis mapping"}

    payload = {
        "nexus_ref_id":       str(case.id),
        "doctor_nexus_uuid":  str(person.id),
        "year":               year,
        "month":              month,
        "amount":             float(abs(case.amount or 0)),
        "description":        case.description or f"Záloha NEXUS #{case.id[:8]}",
        "advance_type":       "záloha" if case.case_type == "advance" else "korekce",
    }
    req = urllib.request.Request(
        f"{FORTIS_URL}/api/inbound/nexus-advance",
        data=_json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        return _json.loads(resp.read())
    except Exception as e:
        return {"status": "error", "reason": str(e)}
"""Wave 2.4 — Deduction → Payroll Staging routes"""
import os, io, csv
from datetime import datetime, date
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity, AuditLog
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from backend.modules.fleet.models import DeductionCase, Vehicle
from backend.modules.attendance.models import PayrollExportBatch, PayrollBatchStatus

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(tags=["deductions"])


def _ctx(d: dict) -> dict:
    d.setdefault("now_date", date.today().isoformat())
    d.setdefault("active_section", "fleet")
    return d


# ── GLOBAL DEDUCTION LIST ─────────────────────────────────────────────────
@router.get("/fleet/deductions", response_class=HTMLResponse)
def deduction_list(request: Request,
                   status_filter: str = None,
                   period_filter: str = None,
                   entity_filter: str = None,
                   db: Session = Depends(get_db),
                   cu: CurrentUser = Depends(get_current_user)):
    q = db.query(DeductionCase)
    if status_filter:  q = q.filter(DeductionCase.status == status_filter)
    if period_filter:  q = q.filter(DeductionCase.payroll_period_target == period_filter)
    if entity_filter:  q = q.filter(DeductionCase.entity_id == entity_filter)
    cases = q.order_by(DeductionCase.created_at.desc()).all()

    # Enrich
    enriched = []
    for c in cases:
        p  = db.query(Person).filter(Person.id == c.person_id).first()
        v  = db.query(Vehicle).filter(Vehicle.id == c.vehicle_id).first() if c.vehicle_id else None
        ent = db.query(Entity).filter(Entity.id == c.entity_id).first() if c.entity_id else None
        enriched.append({"case": c, "person": p, "vehicle": v, "entity": ent})

    # Distinct periods for filter dropdown
    periods = sorted({c.payroll_period_target for c in db.query(DeductionCase).all()
                      if c.payroll_period_target}, reverse=True)
    entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()

    # Counts for fleet board card (pending approval)
    pending_count = db.query(DeductionCase).filter(
        DeductionCase.status.in_(["draft", "pending_approval"])
    ).count()

    return templates.TemplateResponse("pages/fleet/deductions.html", _ctx({
        "request": request, "current_user": cu,
        "enriched": enriched,
        "status_filter": status_filter or "",
        "period_filter": period_filter or "",
        "entity_filter": entity_filter or "",
        "periods": periods,
        "entities": entities,
        "pending_count": pending_count,
    }))


# ── EXPORT BATCH ──────────────────────────────────────────────────────────
@router.post("/fleet/deductions/export-batch")
def export_deduction_batch(
    payroll_period: str = Form(...),
    db: Session = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    if not cu.has_role("owner", "admin", "hr", "finance"):
        raise HTTPException(403)

    # Select all approved deductions for this period
    cases = db.query(DeductionCase).filter(
        DeductionCase.status == "approved",
        DeductionCase.payroll_period_target == payroll_period,
        DeductionCase.export_batch_id == None,  # not yet exported
    ).all()

    if not cases:
        raise HTTPException(400, f"No approved deductions for period {payroll_period}")

    # Create PayrollExportBatch (reuse existing model)
    from backend.core.models.kernel import Entity as KEntity
    batch = PayrollExportBatch(
        period_id="fleet-deductions",   # no period FK for fleet deductions
        entity_id=None,
        status="exported",
        row_count=len(cases),
        exported_by_id=cu.person_id,
        exported_at=datetime.utcnow(),
    )
    db.add(batch); db.flush()

    # Build CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Příjmení", "Jméno", "Email",
        "Typ srážky", "Vozidlo SPZ",
        "Částka", "Důvod",
        "Payroll období", "Zdroj ref"
    ])

    now = datetime.utcnow()
    for c in cases:
        p = db.query(Person).filter(Person.id == c.person_id).first()
        v = db.query(Vehicle).filter(Vehicle.id == c.vehicle_id).first() if c.vehicle_id else None
        writer.writerow([
            p.last_name  if p else "",
            p.first_name if p else "",
            p.email_work or (p.email_personal or "") if p else "",
            c.case_type or "",
            v.spz if v else "",
            str(c.amount or ""),
            c.description or "",
            c.payroll_period_target or "",
            c.id,
        ])
        # Mark exported
        c.export_batch_id = batch.id
        c.status = "exported"
        c.exported_at = now
        c.exported_by = cu.email

    # Save file
    export_dir = os.environ.get("EXPORT_DIR", "") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "exports"
    )
    os.makedirs(export_dir, exist_ok=True)
    fname = f"deductions_{payroll_period}.csv"
    fpath = os.path.join(export_dir, fname)
    with open(fpath, "w", encoding="utf-8-sig", newline="") as f:
        f.write(buf.getvalue())

    batch.file_path = fpath
    db.commit()

    audit(db, "EXPORT", "payroll_export_batch", batch.id, cu.id, cu.email,
          detail=f"fleet_deductions period={payroll_period} rows={len(cases)} file={fname}")

    # Return success summary as plain text / redirect
    return RedirectResponse(
        f"/fleet/deductions?period_filter={payroll_period}&_msg=Exported+{len(cases)}+rows",
        status_code=303
    )
