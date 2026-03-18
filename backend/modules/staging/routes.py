import os
from datetime import date, datetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity, AuditLog
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from backend.modules.staging.models import (
    ImportBatch, ImportRowIssue,
    StgPersonIntake, StgPayrollMonthly, StgVehicleRegistry, StgFuelMonthly
)
from backend.modules.fleet.models import Vehicle

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(prefix="/import", tags=["staging"])

def _ctx(d):
    d.setdefault("now_date", date.today().isoformat())
    d.setdefault("active_section", "import")
    return d

# ── IMPORT CENTER ──────────────────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
def import_center(request: Request, db: Session = Depends(get_db),
                  cu: CurrentUser = Depends(get_current_user)):
    batches = db.query(ImportBatch).order_by(ImportBatch.imported_at.desc()).all()
    return templates.TemplateResponse("pages/staging/import_center.html",
                                      _ctx({"request": request, "current_user": cu, "batches": batches}))

# ── BATCH DETAIL ──────────────────────────────────────────────────────────
@router.get("/{batch_id}", response_class=HTMLResponse)
def batch_detail(batch_id: str, request: Request, db: Session = Depends(get_db),
                 cu: CurrentUser = Depends(get_current_user)):
    batch = db.query(ImportBatch).options(joinedload(ImportBatch.issues)).filter(
        ImportBatch.id == batch_id).first()
    if not batch: raise HTTPException(404)
    rows = []
    if batch.source_type == "people":
        rows = db.query(StgPersonIntake).filter(StgPersonIntake.batch_id == batch_id).all()
    elif batch.source_type == "payroll":
        rows = db.query(StgPayrollMonthly).filter(StgPayrollMonthly.batch_id == batch_id).all()
    elif batch.source_type == "fleet":
        rows = db.query(StgVehicleRegistry).filter(StgVehicleRegistry.batch_id == batch_id).all()
    elif batch.source_type == "fuel":
        rows = db.query(StgFuelMonthly).filter(StgFuelMonthly.batch_id == batch_id).all()
    sc = {}
    for r in rows: s = r.status; sc[s] = sc.get(s, 0) + 1
    return templates.TemplateResponse("pages/staging/batch_detail.html",
        _ctx({"request": request, "current_user": cu, "batch": batch, "rows": rows, "status_counts": sc}))

# ── ISSUES ────────────────────────────────────────────────────────────────
@router.get("/{batch_id}/issues", response_class=HTMLResponse)
def batch_issues(batch_id: str, request: Request, db: Session = Depends(get_db),
                 cu: CurrentUser = Depends(get_current_user)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch: raise HTTPException(404)
    issues = db.query(ImportRowIssue).filter(ImportRowIssue.batch_id == batch_id).order_by(
        ImportRowIssue.severity, ImportRowIssue.source_row_ref).all()
    return templates.TemplateResponse("pages/staging/issues.html",
        _ctx({"request": request, "current_user": cu, "batch": batch, "issues": issues}))

@router.post("/{batch_id}/issues/{issue_id}/resolve")
def resolve_issue(batch_id: str, issue_id: str, resolved_note: str = Form(None),
                  db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    iss = db.query(ImportRowIssue).filter(ImportRowIssue.id == issue_id).first()
    if not iss: raise HTTPException(404)
    iss.resolved_flag = True; iss.resolved_note = resolved_note
    db.commit()
    audit(db, "RESOLVE", "import_row_issue", issue_id, cu.id, cu.email)
    return RedirectResponse(f"/import/{batch_id}/issues", status_code=303)

# ── STAGING PEOPLE ────────────────────────────────────────────────────────
@router.get("/{batch_id}/people", response_class=HTMLResponse)
def staging_people(batch_id: str, request: Request, status_filter: str = None,
                   db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch: raise HTTPException(404)
    q = db.query(StgPersonIntake).filter(StgPersonIntake.batch_id == batch_id)
    if status_filter: q = q.filter(StgPersonIntake.status == status_filter)
    rows = q.order_by(StgPersonIntake.source_row_ref).all()
    people = db.query(Person).filter(Person.is_active == True).order_by(Person.last_name).all()
    return templates.TemplateResponse("pages/staging/staging_people.html",
        _ctx({"request": request, "current_user": cu, "batch": batch,
              "rows": rows, "people": people, "status_filter": status_filter or ""}))

@router.post("/{batch_id}/people/{row_id}/link")
def link_person(batch_id: str, row_id: str, person_id: str = Form(...),
                db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    row = db.query(StgPersonIntake).filter(StgPersonIntake.id == row_id).first()
    if not row: raise HTTPException(404)
    row.candidate_person_id = person_id; row.match_confidence = "manual"; row.status = "reviewed"
    db.commit()
    audit(db, "LINK", "stg_person_intake", row_id, cu.id, cu.email, detail=f"person={person_id}")
    return RedirectResponse(f"/import/{batch_id}/people", status_code=303)

@router.post("/{batch_id}/people/{row_id}/mark-new")
def mark_new(batch_id: str, row_id: str, db: Session = Depends(get_db),
             cu: CurrentUser = Depends(get_current_user)):
    row = db.query(StgPersonIntake).filter(StgPersonIntake.id == row_id).first()
    if not row: raise HTTPException(404)
    row.status = "reviewed"; row.match_confidence = "none"
    db.commit()
    audit(db, "MARK_NEW", "stg_person_intake", row_id, cu.id, cu.email)
    return RedirectResponse(f"/import/{batch_id}/people", status_code=303)

@router.post("/{batch_id}/people/{row_id}/apply")
def apply_person(batch_id: str, row_id: str, db: Session = Depends(get_db),
                 cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner","admin"): raise HTTPException(403)
    row = db.query(StgPersonIntake).filter(StgPersonIntake.id == row_id).first()
    if not row: raise HTTPException(404)
    if row.status not in ("reviewed","matched"): raise HTTPException(400, "Must be reviewed first")
    if row.candidate_person_id and row.match_confidence != "none":
        row.status = "applied"
        db.commit()
        audit(db, "APPLY", "stg_person_intake", row_id, cu.id, cu.email,
              detail=f"linked={row.candidate_person_id}")
    else:
        p = Person(first_name=row.first_name or "", last_name=row.last_name or "",
                   title_before=row.title_before, email_work=row.email_raw,
                   phone=row.phone_raw, is_active=True)
        db.add(p); db.flush()
        row.candidate_person_id = p.id; row.status = "applied"
        db.commit()
        audit(db, "CREATE", "person", p.id, cu.id, cu.email, detail=f"from_stg={row_id}")
    return RedirectResponse(f"/import/{batch_id}/people", status_code=303)

# ── STAGING FLEET ─────────────────────────────────────────────────────────
@router.get("/{batch_id}/fleet", response_class=HTMLResponse)
def staging_fleet(batch_id: str, request: Request, status_filter: str = None,
                  db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch: raise HTTPException(404)
    q = db.query(StgVehicleRegistry).filter(StgVehicleRegistry.batch_id == batch_id)
    if status_filter: q = q.filter(StgVehicleRegistry.status == status_filter)
    rows = q.order_by(StgVehicleRegistry.source_row_ref).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.spz).all()
    people = db.query(Person).filter(Person.is_active == True).order_by(Person.last_name).all()
    return templates.TemplateResponse("pages/staging/staging_fleet.html",
        _ctx({"request": request, "current_user": cu, "batch": batch,
              "rows": rows, "vehicles": vehicles, "people": people,
              "status_filter": status_filter or ""}))

@router.post("/{batch_id}/fleet/{row_id}/link")
def link_fleet(batch_id: str, row_id: str, vehicle_id: str = Form(None),
               person_id: str = Form(None), db: Session = Depends(get_db),
               cu: CurrentUser = Depends(get_current_user)):
    row = db.query(StgVehicleRegistry).filter(StgVehicleRegistry.id == row_id).first()
    if not row: raise HTTPException(404)
    if vehicle_id: row.candidate_vehicle_id = vehicle_id
    if person_id: row.candidate_person_id = person_id
    row.status = "reviewed"; db.commit()
    audit(db, "LINK", "stg_vehicle_registry", row_id, cu.id, cu.email,
          detail=f"v={vehicle_id} p={person_id}")
    return RedirectResponse(f"/import/{batch_id}/fleet", status_code=303)

@router.post("/{batch_id}/fleet/{row_id}/ignore")
def ignore_fleet(batch_id: str, row_id: str, db: Session = Depends(get_db),
                 cu: CurrentUser = Depends(get_current_user)):
    row = db.query(StgVehicleRegistry).filter(StgVehicleRegistry.id == row_id).first()
    if not row: raise HTTPException(404)
    row.status = "ignored"; db.commit()
    audit(db, "IGNORE", "stg_vehicle_registry", row_id, cu.id, cu.email)
    return RedirectResponse(f"/import/{batch_id}/fleet", status_code=303)

# ── STAGING PAYROLL ───────────────────────────────────────────────────────
@router.get("/{batch_id}/payroll", response_class=HTMLResponse)
def staging_payroll(batch_id: str, request: Request, status_filter: str = None,
                    db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch: raise HTTPException(404)
    q = db.query(StgPayrollMonthly).filter(StgPayrollMonthly.batch_id == batch_id)
    if status_filter: q = q.filter(StgPayrollMonthly.status == status_filter)
    rows = q.order_by(StgPayrollMonthly.source_row_ref).all()
    people = db.query(Person).filter(Person.is_active == True).order_by(Person.last_name).all()
    return templates.TemplateResponse("pages/staging/staging_payroll.html",
        _ctx({"request": request, "current_user": cu, "batch": batch,
              "rows": rows, "people": people, "status_filter": status_filter or ""}))

@router.post("/{batch_id}/payroll/{row_id}/link")
def link_payroll(batch_id: str, row_id: str, person_id: str = Form(...),
                 db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    row = db.query(StgPayrollMonthly).filter(StgPayrollMonthly.id == row_id).first()
    if not row: raise HTTPException(404)
    row.candidate_person_id = person_id; row.status = "reviewed"; db.commit()
    audit(db, "LINK", "stg_payroll_monthly", row_id, cu.id, cu.email, detail=f"person={person_id}")
    return RedirectResponse(f"/import/{batch_id}/payroll", status_code=303)

@router.post("/{batch_id}/payroll/{row_id}/ignore")
def ignore_payroll(batch_id: str, row_id: str, db: Session = Depends(get_db),
                   cu: CurrentUser = Depends(get_current_user)):
    row = db.query(StgPayrollMonthly).filter(StgPayrollMonthly.id == row_id).first()
    if not row: raise HTTPException(404)
    row.status = "ignored"; db.commit()
    audit(db, "IGNORE", "stg_payroll_monthly", row_id, cu.id, cu.email)
    return RedirectResponse(f"/import/{batch_id}/payroll", status_code=303)


# ── STAGING FUEL ──────────────────────────────────────────────────────────
@router.get("/{batch_id}/fuel", response_class=HTMLResponse)
def staging_fuel(batch_id: str, request: Request, status_filter: str = None,
                 db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    from backend.modules.fleet.models import Vehicle, FuelCard
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch: raise HTTPException(404)
    q = db.query(StgFuelMonthly).filter(StgFuelMonthly.batch_id == batch_id)
    if status_filter: q = q.filter(StgFuelMonthly.status == status_filter)
    rows = q.order_by(StgFuelMonthly.source_row_ref).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.spz).all()
    people = db.query(Person).filter(Person.is_active == True).order_by(Person.last_name).all()
    entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()
    return templates.TemplateResponse("pages/staging/staging_fuel.html", _ctx({
        "request": request, "current_user": cu,
        "batch": batch, "rows": rows, "vehicles": vehicles,
        "people": people, "entities": entities,
        "status_filter": status_filter or "",
    }))


@router.post("/{batch_id}/fuel/{row_id}/assign")
def assign_fuel_row(batch_id: str, row_id: str,
                    vehicle_id: str = Form(None), person_id: str = Form(None),
                    entity_id: str = Form(None),
                    db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    row = db.query(StgFuelMonthly).filter(StgFuelMonthly.id == row_id).first()
    if not row: raise HTTPException(404)
    if vehicle_id: row.candidate_vehicle_id = vehicle_id
    if person_id: row.candidate_person_id = person_id
    if entity_id: row.company_hint = entity_id  # reuse field for assignment
    row.status = "reviewed"
    db.commit()
    audit(db, "ASSIGN", "stg_fuel_monthly", row_id, cu.id, cu.email,
          detail=f"v={vehicle_id} p={person_id}")
    return RedirectResponse(f"/import/{batch_id}/fuel", status_code=303)


@router.post("/{batch_id}/fuel/{row_id}/apply")
def apply_fuel_row(batch_id: str, row_id: str,
                   db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    """Promote reviewed/matched staging row → canonical FuelTransaction."""
    from backend.modules.fleet.models import FuelTransaction, FuelCard
    row = db.query(StgFuelMonthly).filter(StgFuelMonthly.id == row_id).first()
    if not row: raise HTTPException(404)
    if not row.candidate_vehicle_id:
        raise HTTPException(400, "Must have candidate vehicle before apply")
    if row.status not in ("matched", "reviewed"):
        raise HTTPException(400, f"Status {row.status} — must be matched or reviewed")

    # Lookup card
    card = None
    if row.candidate_card_id:
        card = db.query(FuelCard).filter(FuelCard.id == row.candidate_card_id).first()

    # Lookup entity from vehicle's entity
    from backend.modules.fleet.models import Vehicle
    vehicle = db.query(Vehicle).filter(Vehicle.id == row.candidate_vehicle_id).first()
    entity_id = None
    if vehicle:
        from backend.core.models.kernel import EntityMembership
        # get entity from vehicle via entity_id field if it exists
        entity_id = getattr(vehicle, 'entity_id', None)

    ft = FuelTransaction(
        vehicle_id=row.candidate_vehicle_id,
        driver_person_id=None,
        entity_id=entity_id,
        fuel_card_id=row.candidate_card_id,
        month=row.month,
        year=row.year,
        amount_total=float(row.amount_total) if row.amount_total else None,
        liters_total=float(row.liters_total) if row.liters_total else None,
        source_doc_ref=row.source_doc_ref,
        source_staging_id=row.id,
        status="approved",
        reviewed_by=cu.email,
    )
    db.add(ft)
    row.status = "applied"
    db.commit()
    audit(db, "APPLY", "fuel_transaction", ft.id, cu.id, cu.email,
          detail=f"from_stg={row_id} vehicle={row.candidate_vehicle_id}")
    return RedirectResponse(f"/import/{batch_id}/fuel", status_code=303)


@router.post("/{batch_id}/fuel/{row_id}/ignore")
def ignore_fuel_row(batch_id: str, row_id: str,
                    db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    row = db.query(StgFuelMonthly).filter(StgFuelMonthly.id == row_id).first()
    if not row: raise HTTPException(404)
    row.status = "ignored"
    db.commit()
    audit(db, "IGNORE", "stg_fuel_monthly", row_id, cu.id, cu.email)
    return RedirectResponse(f"/import/{batch_id}/fuel", status_code=303)
