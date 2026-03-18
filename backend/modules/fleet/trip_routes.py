"""Wave 2.5 — Trip Log / Kniha jízd routes"""
import os
from datetime import datetime, date
from calendar import monthrange
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from backend.modules.fleet.models import TripLog, Vehicle

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(tags=["trips"])


def _ctx(d):
    d.setdefault("now_date", date.today().isoformat())
    d.setdefault("active_section", "fleet")
    return d


def _month_bounds(year: int, month: int):
    _, last = monthrange(year, month)
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"


def _trip_summary(db: Session, person_id: str = None, vehicle_id: str = None,
                  year: int = None, month: int = None) -> dict:
    q = db.query(TripLog).filter(TripLog.status != "ignored")
    if person_id:  q = q.filter(TripLog.person_id == person_id)
    if vehicle_id: q = q.filter(TripLog.vehicle_id == vehicle_id)
    if year and month:
        d_from, d_to = _month_bounds(year, month)
        q = q.filter(TripLog.trip_date >= d_from, TripLog.trip_date <= d_to)
    trips = q.all()
    total_km = sum(t.distance_km or 0 for t in trips)
    biz_km   = sum(t.distance_km or 0 for t in trips if t.trip_type == "business")
    priv_km  = sum(t.distance_km or 0 for t in trips if t.trip_type == "private")
    return {"count": len(trips), "total_km": total_km,
            "business_km": biz_km, "private_km": priv_km}


# ── GLOBAL TRIPS LIST ─────────────────────────────────────────────────────
@router.get("/fleet/trips", response_class=HTMLResponse)
def trip_list(request: Request,
              driver_filter: str = None, vehicle_filter: str = None,
              entity_filter: str = None, type_filter: str = None,
              status_filter: str = None, date_from: str = None, date_to: str = None,
              db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    q = db.query(TripLog)
    if driver_filter:  q = q.filter(TripLog.person_id == driver_filter)
    if vehicle_filter: q = q.filter(TripLog.vehicle_id == vehicle_filter)
    if type_filter:    q = q.filter(TripLog.trip_type == type_filter)
    if status_filter:  q = q.filter(TripLog.status == status_filter)
    if date_from:      q = q.filter(TripLog.trip_date >= date_from)
    if date_to:        q = q.filter(TripLog.trip_date <= date_to)
    trips = q.order_by(TripLog.trip_date.desc()).all()

    # Pending count
    pending = db.query(TripLog).filter(TripLog.status.in_(["draft","submitted"])).count()

    # Monthly summary (current month)
    today = date.today()
    summary = _trip_summary(db, year=today.year, month=today.month)

    people   = db.query(Person).filter(Person.is_active==True).order_by(Person.last_name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.spz).all()
    entities = db.query(Entity).filter(Entity.is_active==True).order_by(Entity.code).all()

    return templates.TemplateResponse("pages/fleet/trips.html", _ctx({
        "request": request, "current_user": cu,
        "trips": trips, "people": people, "vehicles": vehicles, "entities": entities,
        "driver_filter": driver_filter or "", "vehicle_filter": vehicle_filter or "",
        "type_filter": type_filter or "", "status_filter": status_filter or "",
        "date_from": date_from or "", "date_to": date_to or "",
        "pending": pending, "summary": summary,
    }))


# ── CREATE TRIP ───────────────────────────────────────────────────────────
@router.post("/fleet/trips/new")
def create_trip(
    person_id: str = Form(...), vehicle_id: str = Form(...),
    entity_id: str = Form(None), trip_date: str = Form(...),
    start_km: int = Form(None), end_km: int = Form(None),
    trip_type: str = Form("business"), purpose: str = Form(None),
    destination: str = Form(None), cost_center: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)
):
    # Validation
    if start_km is not None and end_km is not None:
        if end_km < start_km:
            raise HTTPException(400, "end_km must be >= start_km")
        distance = end_km - start_km
    else:
        distance = None

    t = TripLog(
        person_id=person_id, vehicle_id=vehicle_id,
        entity_id=entity_id or None, trip_date=trip_date,
        start_km=start_km, end_km=end_km, distance_km=distance,
        trip_type=trip_type, purpose=purpose, destination=destination,
        cost_center=cost_center, notes=notes,
        status="submitted", source="manual", created_by_id=cu.person_id
    )
    db.add(t); db.commit()
    audit(db, "CREATE", "trip_log", t.id, cu.id, cu.email,
          detail=f"vehicle={vehicle_id} date={trip_date} km={distance} type={trip_type}")
    return RedirectResponse("/fleet/trips", status_code=303)


# ── APPROVE TRIP ──────────────────────────────────────────────────────────
@router.post("/fleet/trips/{trip_id}/approve")
def approve_trip(trip_id: str, db: Session = Depends(get_db),
                 cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner","admin","manager"): raise HTTPException(403)
    t = db.query(TripLog).filter(TripLog.id == trip_id).first()
    if not t: raise HTTPException(404)
    t.status = "approved"
    t.reviewed_by = cu.email
    t.reviewed_at = datetime.utcnow()
    db.commit()
    audit(db, "APPROVE", "trip_log", t.id, cu.id, cu.email,
          detail=f"km={t.distance_km} date={t.trip_date}")
    return RedirectResponse("/fleet/trips", status_code=303)


# ── IGNORE TRIP ───────────────────────────────────────────────────────────
@router.post("/fleet/trips/{trip_id}/ignore")
def ignore_trip(trip_id: str, db: Session = Depends(get_db),
                cu: CurrentUser = Depends(get_current_user)):
    t = db.query(TripLog).filter(TripLog.id == trip_id).first()
    if not t: raise HTTPException(404)
    t.status = "ignored"
    db.commit()
    audit(db, "IGNORE", "trip_log", t.id, cu.id, cu.email)
    return RedirectResponse("/fleet/trips", status_code=303)


# ── DRIVER TRIP SUMMARY (JSON for driver_detail embed) ───────────────────
def get_driver_trip_context(db: Session, person_id: str) -> dict:
    today = date.today()
    recent = db.query(TripLog).filter(
        TripLog.person_id == person_id, TripLog.status != "ignored"
    ).order_by(TripLog.trip_date.desc()).limit(10).all()
    summary = _trip_summary(db, person_id=person_id, year=today.year, month=today.month)
    return {"driver_trips": recent, "driver_trip_summary": summary}


# ── VEHICLE TRIP SUMMARY (for vehicle_detail embed) ───────────────────────
def get_vehicle_trip_context(db: Session, vehicle_id: str) -> dict:
    today = date.today()
    recent = db.query(TripLog).filter(
        TripLog.vehicle_id == vehicle_id, TripLog.status != "ignored"
    ).order_by(TripLog.trip_date.desc()).limit(10).all()
    summary = _trip_summary(db, vehicle_id=vehicle_id, year=today.year, month=today.month)
    return {"vehicle_trips": recent, "vehicle_trip_summary": summary}
