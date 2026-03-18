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
    # Trips board context
    _tm_from, _tm_to = f'{_now.year}-{_now.month:02d}-01', f'{_now.year}-{_now.month:02d}-28'
    trips_this_month = 0
    trips_pending_approval = 0
    deduction_pending_count = db.query(DeductionCase).filter(
        DeductionCase.status.in_(["draft","pending_approval"])).count()
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
        "trips_this_month": trips_this_month,
        "trips_pending_approval": trips_pending_approval,
        "deduction_pending_count": deduction_pending_count,
        "open_fines_count": open_fines_count,
        "open_claims_count": open_claims_count,
        "missing_odo_count": missing_odo_count,
        "phm_total_kc": phm["total_kc"],
        "phm_total_litres": phm["total_litres"],
        "page_title": "Fleet Board",
    })


