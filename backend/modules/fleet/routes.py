from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from backend.core.models.kernel import Person
from .service import (
    get_all_vehicles, get_vehicle, get_phm_summary, get_canonical_phm_summary,
    get_canonical_phm_by_vehicle, get_top_phm_vehicles, get_phm_by_vehicle,
    get_stk_alerts, log_event, change_driver
)
from .models import Vehicle, VehicleAssignment, FleetEventType, InsuranceClaim, TrafficFine, DeductionCase, OdometerReading, FuelTransaction
import os

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates"))

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.get("", response_class=HTMLResponse)
def fleet_board(request: Request, db: Session = Depends(get_db),
                current_user: CurrentUser = Depends(get_current_user)):
    vehicles = get_all_vehicles(db)
    stk_alerts = get_stk_alerts(db)
    phm = get_phm_summary(db, period="2026-03")
    # Canonical PHM (from approved FuelTransaction)
    from datetime import date as _date
    _now = _date.today()
    phm_canonical = get_canonical_phm_summary(db, month=_now.month, year=_now.year)
    phm_canonical_prev = get_canonical_phm_summary(db, month=_now.month-1 if _now.month>1 else 12, year=_now.year if _now.month>1 else _now.year-1)
    phm_top_vehicles = get_top_phm_vehicles(db, month=_now.month, year=_now.year)
    from backend.modules.staging.models import StgFuelMonthly
    phm_unresolved_count = db.query(StgFuelMonthly).filter(StgFuelMonthly.status=="unresolved", StgFuelMonthly.amount_total != None).count()
    open_fines_count = db.query(TrafficFine).filter(TrafficFine.status=="open").count()
    open_claims_count = db.query(InsuranceClaim).filter(InsuranceClaim.status=="open").count()
    # Missing odometer: drivers with vehicle assignment but no odometer in 45 days
    from datetime import timedelta
    cutoff = (_date.today() - timedelta(days=45)).isoformat()
    _asgn_vids = [r[0] for r in db.query(VehicleAssignment.vehicle_id).filter(VehicleAssignment.date_to == None).distinct().all()]
    missing_odo_count = 0
    for vid in _asgn_vids:
        last = db.query(OdometerReading).filter(OdometerReading.vehicle_id == vid).order_by(OdometerReading.reading_date.desc()).first()
        if not last or last.reading_date < cutoff:
            missing_odo_count += 1
    return templates.TemplateResponse("pages/fleet/board.html", {
        "request": request,
        "current_user": current_user,
        "vehicles": vehicles,
        "stk_alert_count": len(stk_alerts),
        "phm_period": "2026-03",
        "phm_canonical": phm_canonical,
        "phm_canonical_prev": phm_canonical_prev,
        "phm_top_vehicles": phm_top_vehicles,
        "phm_unresolved_count": phm_unresolved_count,
        "open_fines_count": open_fines_count,
        "open_claims_count": open_claims_count,
        "missing_odo_count": missing_odo_count,
        "phm_total_kc": phm["total_kc"],
        "phm_total_litres": phm["total_litres"],
        "page_title": "Fleet Board",
    })


@router.get("/{vehicle_id}", response_class=HTMLResponse)
def vehicle_detail(vehicle_id: str, request: Request, db: Session = Depends(get_db),
                   current_user: CurrentUser = Depends(get_current_user)):
    v = get_vehicle(db, vehicle_id)
    if not v:
        raise HTTPException(404, "Vozidlo nenalezeno")
    phm = get_phm_by_vehicle(db, vehicle_id)
    phm_canonical_txns = get_canonical_phm_by_vehicle(db, vehicle_id)
    return templates.TemplateResponse("pages/fleet/vehicle_detail.html", {
        "request": request,
        "current_user": current_user,
        "v": v,
        "phm_transactions": phm,
        "phm_canonical_txns": phm_canonical_txns,
        "event_types": [e.value for e in FleetEventType],
        "people": db.query(Person).filter(Person.is_active == True).order_by(Person.last_name).all(),
        "page_title": f"{v.make} {v.model}",
    })


@router.post("/{vehicle_id}/event")
def add_event(vehicle_id: str, event_type: str = Form(...), event_date: str = Form(...),
              description: str = Form(None), cost_kc: int = Form(None),
              db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    v = get_vehicle(db, vehicle_id)
    if not v:
        raise HTTPException(404)
    log_event(db, vehicle_id, event_type, event_date, description, cost_kc, current_user.person_id)
    audit(db, "CREATE", "fleet_event", vehicle_id, current_user.id, current_user.email,
          detail=f"{event_type} {event_date}")
    return RedirectResponse(f"/fleet/{vehicle_id}#events", status_code=303)


@router.post("/{vehicle_id}/driver")
def assign_driver(vehicle_id: str, person_id: str = Form(...), date_from: str = Form(...),
                  reason: str = Form(None), db: Session = Depends(get_db),
                  current_user: CurrentUser = Depends(get_current_user)):
    if not current_user.has_role("owner", "admin", "manager", "fleet_manager"):
        raise HTTPException(403)
    change_driver(db, vehicle_id, person_id, date_from, reason, current_user.person_id)
    audit(db, "UPDATE", "vehicle_assignment", vehicle_id, current_user.id, current_user.email,
          detail=f"new driver {person_id} from {date_from}")
    return RedirectResponse(f"/fleet/{vehicle_id}#driver", status_code=303)


@router.post("/{vehicle_id}/edit")
def edit_vehicle(vehicle_id: str, spz: str = Form(None), stk_valid_to: str = Form(None),
                 axigon_card: str = Form(None), km_current: int = Form(None),
                 notes: str = Form(None), status: str = Form(None),
                 db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    if not current_user.has_role("owner", "admin", "fleet_manager"):
        raise HTTPException(403)
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(404)
    if spz is not None: v.spz = spz or None
    if stk_valid_to: v.stk_valid_to = stk_valid_to
    if km_current: v.km_current = km_current
    if notes is not None: v.notes = notes
    if status: v.status = status
    db.commit()
    audit(db, "UPDATE", "vehicle", vehicle_id, current_user.id, current_user.email)
    return RedirectResponse(f"/fleet/{vehicle_id}", status_code=303)
