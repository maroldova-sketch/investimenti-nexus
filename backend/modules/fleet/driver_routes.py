"""Fleet Driver Ops routes — Wave 2.3"""
import os
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity, EntityMembership
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from backend.modules.fleet.models import (
    Vehicle, VehicleAssignment, OdometerReading,
    InsuranceClaim, TrafficFine, DeductionCase, FuelTransaction, TripLog
)

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(tags=["fleet-drivers"])


def _ctx(d: dict) -> dict:
    d.setdefault("now_date", date.today().isoformat())
    d.setdefault("active_section", "fleet")
    return d


def _active_drivers(db: Session):
    """Persons with at least one vehicle assignment (current or historical)."""
    person_ids = db.query(VehicleAssignment.person_id).distinct().all()
    ids = [r[0] for r in person_ids]
    if not ids:
        return []
    return db.query(Person).filter(Person.id.in_(ids), Person.is_active == True).order_by(Person.last_name).all()


def _current_assignment(db: Session, person_id: str):
    return db.query(VehicleAssignment).filter(
        VehicleAssignment.person_id == person_id,
        VehicleAssignment.date_to == None
    ).order_by(VehicleAssignment.date_from.desc()).first()


def _last_odometer(db: Session, vehicle_id: str):
    return db.query(OdometerReading).filter(
        OdometerReading.vehicle_id == vehicle_id
    ).order_by(OdometerReading.reading_date.desc()).first()


# ── DRIVERS LIST ──────────────────────────────────────────────────────────
@router.get("/fleet/drivers", response_class=HTMLResponse)
def driver_list(request: Request, entity_filter: str = None, has_open: str = None,
                db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    drivers = _active_drivers(db)
    entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()

    rows = []
    for p in drivers:
        asgn = _current_assignment(db, p.id)
        vehicle = db.query(Vehicle).filter(Vehicle.id == asgn.vehicle_id).first() if asgn else None
        last_odo = _last_odometer(db, vehicle.id) if vehicle else None
        open_fines = db.query(TrafficFine).filter(
            TrafficFine.driver_person_id == p.id, TrafficFine.status == "open").count()
        open_claims = db.query(InsuranceClaim).filter(
            InsuranceClaim.driver_person_id == p.id, InsuranceClaim.status == "open").count()
        open_deductions = db.query(DeductionCase).filter(
            DeductionCase.person_id == p.id,
            DeductionCase.status.in_(["draft", "pending_approval"])).count()
        # entity membership
        mem = db.query(EntityMembership).filter(EntityMembership.person_id == p.id).first()
        ent = db.query(Entity).filter(Entity.id == mem.entity_id).first() if mem else None

        # odometer warning
        odo_warn = False
        if last_odo:
            try:
                last_dt = datetime.strptime(last_odo.reading_date, "%Y-%m-%d").date()
                odo_warn = (date.today() - last_dt).days > 45
            except: pass
        else:
            odo_warn = True if vehicle else False

        row = {"person": p, "vehicle": vehicle, "assignment": asgn, "entity": ent,
               "last_odo": last_odo, "odo_warn": odo_warn,
               "open_fines": open_fines, "open_claims": open_claims,
               "open_deductions": open_deductions,
               "has_open": open_fines + open_claims + open_deductions > 0}
        rows.append(row)

    if entity_filter:
        rows = [r for r in rows if r["entity"] and r["entity"].code == entity_filter]
    if has_open == "1":
        rows = [r for r in rows if r["has_open"]]

    return templates.TemplateResponse("pages/fleet/drivers.html", _ctx({
        "request": request, "current_user": cu,
        "rows": rows, "entities": entities,
        "entity_filter": entity_filter or "", "has_open": has_open or "",
    }))


# ── DRIVER DETAIL ─────────────────────────────────────────────────────────
@router.get("/fleet/driver/{person_id}", response_class=HTMLResponse)
def driver_detail(person_id: str, request: Request, db: Session = Depends(get_db),
                  cu: CurrentUser = Depends(get_current_user)):
    p = db.query(Person).filter(Person.id == person_id).first()
    if not p: raise HTTPException(404)

    # All assignments
    assignments = db.query(VehicleAssignment).filter(
        VehicleAssignment.person_id == person_id
    ).order_by(VehicleAssignment.date_from.desc()).all()
    vehicle_ids = list({a.vehicle_id for a in assignments})
    vehicles_map = {v.id: v for v in db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()}

    # Current assignment
    current_asgn = next((a for a in assignments if a.date_to is None), None)
    current_vehicle = vehicles_map.get(current_asgn.vehicle_id) if current_asgn else None

    # Entity
    mem = db.query(EntityMembership).filter(EntityMembership.person_id == person_id).first()
    entity = db.query(Entity).filter(Entity.id == mem.entity_id).first() if mem else None

    # PHM — canonical transactions for driver's vehicles during their assignment periods
    phm_txns = db.query(FuelTransaction).filter(
        FuelTransaction.vehicle_id.in_(vehicle_ids),
        FuelTransaction.status == "approved"
    ).order_by(FuelTransaction.year.desc(), FuelTransaction.month.desc()).all()
    phm_total_kc = sum(float(t.amount_total or 0) for t in phm_txns)
    phm_total_l = sum(float(t.liters_total or 0) for t in phm_txns)

    # Fines
    fines = db.query(TrafficFine).filter(
        TrafficFine.driver_person_id == person_id
    ).order_by(TrafficFine.fine_date.desc()).all()

    # Claims
    claims = db.query(InsuranceClaim).filter(
        InsuranceClaim.driver_person_id == person_id
    ).order_by(InsuranceClaim.claim_date.desc()).all()

    # Deductions
    deductions = db.query(DeductionCase).filter(
        DeductionCase.person_id == person_id
    ).order_by(DeductionCase.created_at.desc()).all()

    # Odometer
    last_odo = None
    odo_days = None
    odo_warn = False
    if current_vehicle:
        last_odo = _last_odometer(db, current_vehicle.id)
        if last_odo:
            try:
                last_dt = datetime.strptime(last_odo.reading_date, "%Y-%m-%d").date()
                odo_days = (date.today() - last_dt).days
                odo_warn = odo_days > 45
            except: pass
        else:
            odo_warn = True

    # All vehicles for forms
    all_vehicles = db.query(Vehicle).order_by(Vehicle.spz).all()
    all_entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()
    all_people = db.query(Person).filter(Person.is_active == True).order_by(Person.last_name).all()

    open_alerts = sum([
        db.query(TrafficFine).filter(TrafficFine.driver_person_id == person_id, TrafficFine.status == "open").count(),
        db.query(InsuranceClaim).filter(InsuranceClaim.driver_person_id == person_id, InsuranceClaim.status == "open").count(),
        1 if odo_warn else 0,
    ])

    # Trip context
    from calendar import monthrange as _mr
    today_d = date.today()
    _tf, _tt = f'{today_d.year}-{today_d.month:02d}-01', f'{today_d.year}-{today_d.month:02d}-{_mr(today_d.year, today_d.month)[1]:02d}'
    driver_trips = db.query(TripLog).filter(
        TripLog.person_id == person_id, TripLog.status != 'ignored',
        TripLog.trip_date >= _tf, TripLog.trip_date <= _tt
    ).order_by(TripLog.trip_date.desc()).limit(8).all()
    _all_trips = db.query(TripLog).filter(TripLog.person_id == person_id, TripLog.status != 'ignored').all()
    driver_trip_summary = {
        "count": len(_all_trips),
        "total_km": sum(t.distance_km or 0 for t in _all_trips),
        "business_km": sum(t.distance_km or 0 for t in _all_trips if t.trip_type == 'business'),
        "private_km": sum(t.distance_km or 0 for t in _all_trips if t.trip_type == 'private'),
    }

    return templates.TemplateResponse("pages/fleet/driver_detail.html", _ctx({
        "request": request, "current_user": cu,
        "p": p, "entity": entity,
        "assignments": assignments, "vehicles_map": vehicles_map,
        "current_asgn": current_asgn, "current_vehicle": current_vehicle,
        "phm_txns": phm_txns, "phm_total_kc": phm_total_kc, "phm_total_l": phm_total_l,
        "fines": fines, "claims": claims, "deductions": deductions,
        "last_odo": last_odo, "odo_days": odo_days, "odo_warn": odo_warn,
        "open_alerts": open_alerts,
        "driver_trips": driver_trips,
        "driver_trip_summary": driver_trip_summary,
        "all_vehicles": all_vehicles, "all_entities": all_entities, "all_people": all_people,
    }))


# ── ODOMETER ──────────────────────────────────────────────────────────────
@router.post("/fleet/driver/{person_id}/odometer")
def submit_odometer(person_id: str, vehicle_id: str = Form(...),
                    km: int = Form(...), reading_date: str = Form(...),
                    notes: str = Form(None),
                    db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    odo = OdometerReading(vehicle_id=vehicle_id, km=km, reading_date=reading_date,
                          recorded_by_id=cu.person_id, notes=notes)
    db.add(odo); db.commit()
    audit(db, "CREATE", "odometer_reading", odo.id, cu.id, cu.email,
          detail=f"vehicle={vehicle_id} km={km} date={reading_date}")
    return RedirectResponse(f"/fleet/driver/{person_id}", status_code=303)


# ── INSURANCE CLAIM ───────────────────────────────────────────────────────
@router.post("/fleet/{vehicle_id}/claim/new")
def create_claim(vehicle_id: str, driver_person_id: str = Form(None),
                 entity_id: str = Form(None), claim_date: str = Form(...),
                 location: str = Form(None), description: str = Form(None),
                 insurer_ref: str = Form(None), amount_claimed: float = Form(None),
                 db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    c = InsuranceClaim(vehicle_id=vehicle_id, driver_person_id=driver_person_id or None,
                       entity_id=entity_id or None, claim_date=claim_date,
                       location=location, description=description, insurer_ref=insurer_ref,
                       amount_claimed=amount_claimed, status="open",
                       created_by_id=cu.person_id)
    db.add(c); db.commit()
    audit(db, "CREATE", "insurance_claim", c.id, cu.id, cu.email,
          detail=f"vehicle={vehicle_id} date={claim_date}")
    # Redirect back to vehicle or driver
    if driver_person_id:
        return RedirectResponse(f"/fleet/driver/{driver_person_id}", status_code=303)
    return RedirectResponse(f"/fleet/{vehicle_id}", status_code=303)


# ── TRAFFIC FINE ──────────────────────────────────────────────────────────
@router.post("/fleet/{vehicle_id}/fine/new")
def create_fine(vehicle_id: str, driver_person_id: str = Form(None),
                entity_id: str = Form(None), fine_date: str = Form(...),
                amount: float = Form(None), reason: str = Form(None),
                due_date: str = Form(None),
                db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    f = TrafficFine(vehicle_id=vehicle_id, driver_person_id=driver_person_id or None,
                    entity_id=entity_id or None, fine_date=fine_date,
                    amount=amount, reason=reason, due_date=due_date,
                    status="open", created_by_id=cu.person_id)
    db.add(f); db.commit()
    audit(db, "CREATE", "traffic_fine", f.id, cu.id, cu.email,
          detail=f"vehicle={vehicle_id} amount={amount} date={fine_date}")
    if driver_person_id:
        return RedirectResponse(f"/fleet/driver/{driver_person_id}", status_code=303)
    return RedirectResponse(f"/fleet/{vehicle_id}", status_code=303)


# ── DEDUCTION CASE ────────────────────────────────────────────────────────
@router.post("/fleet/deduction/new")
def create_deduction(person_id: str = Form(...), vehicle_id: str = Form(None),
                     entity_id: str = Form(None), case_type: str = Form(...),
                     amount: float = Form(None), description: str = Form(None),
                     payroll_period_target: str = Form(None),
                     source_ref_type: str = Form(None), source_ref_id: str = Form(None),
                     db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    d = DeductionCase(person_id=person_id, vehicle_id=vehicle_id or None,
                      entity_id=entity_id or None, case_type=case_type,
                      amount=amount, description=description,
                      payroll_period_target=payroll_period_target,
                      source_ref_type=source_ref_type, source_ref_id=source_ref_id,
                      status="draft", created_by_id=cu.person_id)
    db.add(d); db.commit()
    audit(db, "CREATE", "deduction_case", d.id, cu.id, cu.email,
          detail=f"person={person_id} type={case_type} amount={amount}")
    return RedirectResponse(f"/fleet/driver/{person_id}", status_code=303)


@router.post("/fleet/deduction/{deduction_id}/approve")
def approve_deduction(deduction_id: str, db: Session = Depends(get_db),
                      cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner", "admin", "manager"): raise HTTPException(403)
    d = db.query(DeductionCase).filter(DeductionCase.id == deduction_id).first()
    if not d: raise HTTPException(404)
    d.status = "approved"
    d.reviewed_by = cu.email
    d.reviewed_at = datetime.utcnow()
    db.commit()
    audit(db, "APPROVE", "deduction_case", d.id, cu.id, cu.email,
          detail=f"amount={d.amount}")
    return RedirectResponse(f"/fleet/driver/{d.person_id}", status_code=303)


@router.post("/fleet/deduction/{deduction_id}/export")
def export_deduction(deduction_id: str, db: Session = Depends(get_db),
                     cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner", "admin", "hr", "finance"): raise HTTPException(403)
    d = db.query(DeductionCase).filter(DeductionCase.id == deduction_id).first()
    if not d: raise HTTPException(404)
    if d.status != "approved": raise HTTPException(400, "Must be approved first")
    d.status = "exported"
    db.commit()
    audit(db, "EXPORT", "deduction_case", d.id, cu.id, cu.email,
          detail=f"payroll_period={d.payroll_period_target}")
    return RedirectResponse(f"/fleet/driver/{d.person_id}", status_code=303)
