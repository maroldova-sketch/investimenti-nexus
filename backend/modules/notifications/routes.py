"""Wave 3.0 — Notification + Intake routes."""
import os
from datetime import datetime, date
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity, AuditLog
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from backend.modules.notifications.models import Notification, NotificationDelivery, IntakeRecord
from backend.modules.notifications.service import (
    generate_odometer_notifications, generate_compliance_notifications,
    generate_deduction_notifications, generate_fuel_review_notifications
)

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(tags=["notifications"])


def _ctx(d: dict) -> dict:
    d.setdefault("now_date", date.today().isoformat())
    d.setdefault("active_section", "notifications")
    return d


# ── NOTIFICATION CENTER ────────────────────────────────────────────────────
@router.get("/notifications", response_class=HTMLResponse)
def notification_center(request: Request,
                         status_filter: str = None, severity_filter: str = None,
                         type_filter: str = None,
                         db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    q = db.query(Notification)
    if status_filter:   q = q.filter(Notification.status == status_filter)
    if severity_filter: q = q.filter(Notification.severity == severity_filter)
    if type_filter:     q = q.filter(Notification.related_type == type_filter)
    notifications = q.order_by(Notification.created_at.desc()).all()

    # Enrich with person/entity
    enriched = []
    for n in notifications:
        p   = db.query(Person).filter(Person.id == n.person_id).first() if n.person_id else None
        ent = db.query(Entity).filter(Entity.id == n.entity_id).first() if n.entity_id else None
        enriched.append({"n": n, "person": p, "entity": ent})

    new_count = db.query(Notification).filter(Notification.status == "new").count()
    entities  = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()

    return templates.TemplateResponse("pages/notifications/center.html", _ctx({
        "request": request, "current_user": cu,
        "enriched": enriched, "new_count": new_count, "entities": entities,
        "status_filter": status_filter or "", "severity_filter": severity_filter or "",
        "type_filter": type_filter or "",
    }))


@router.post("/notifications/{notif_id}/read")
def mark_read(notif_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notif_id).first()
    if not n: raise HTTPException(404)
    n.status = "read"; n.read_at = datetime.utcnow()
    db.commit()
    audit(db, "READ", "notification", notif_id, cu.id, cu.email)
    return RedirectResponse("/notifications", status_code=303)


@router.post("/notifications/{notif_id}/acknowledge")
def acknowledge(notif_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notif_id).first()
    if not n: raise HTTPException(404)
    n.status = "acknowledged"; n.acknowledged_at = datetime.utcnow()
    db.commit()
    audit(db, "ACKNOWLEDGE", "notification", notif_id, cu.id, cu.email)
    return RedirectResponse("/notifications", status_code=303)


@router.post("/notifications/{notif_id}/close")
def close_notification(notif_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notif_id).first()
    if not n: raise HTTPException(404)
    n.status = "closed"; n.closed_at = datetime.utcnow(); n.closed_by = cu.email
    db.commit()
    audit(db, "CLOSE", "notification", notif_id, cu.id, cu.email)
    return RedirectResponse("/notifications", status_code=303)


# ── NOTIFICATION GENERATORS (triggered via admin button) ───────────────────
@router.post("/notifications/generate/odometer")
def gen_odometer(db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    count = generate_odometer_notifications(db)
    audit(db, "GENERATE", "notification", None, cu.id, cu.email, detail=f"odometer count={count}")
    return RedirectResponse("/notifications", status_code=303)


@router.post("/notifications/generate/compliance")
def gen_compliance(db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    count = generate_compliance_notifications(db)
    audit(db, "GENERATE", "notification", None, cu.id, cu.email, detail=f"compliance count={count}")
    return RedirectResponse("/notifications", status_code=303)


@router.post("/notifications/generate/deductions")
def gen_deductions(db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    count = generate_deduction_notifications(db)
    audit(db, "GENERATE", "notification", None, cu.id, cu.email, detail=f"deductions count={count}")
    return RedirectResponse("/notifications", status_code=303)


@router.post("/notifications/generate/fuel")
def gen_fuel(db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    count = generate_fuel_review_notifications(db)
    audit(db, "GENERATE", "notification", None, cu.id, cu.email, detail=f"fuel count={count}")
    return RedirectResponse("/notifications", status_code=303)


@router.post("/notifications/generate/all")
def gen_all(db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    total = (generate_odometer_notifications(db) +
             generate_compliance_notifications(db) +
             generate_deduction_notifications(db) +
             generate_fuel_review_notifications(db))
    audit(db, "GENERATE", "notification", None, cu.id, cu.email, detail=f"all count={total}")
    return RedirectResponse("/notifications", status_code=303)


# ── INTAKE RECORDS ─────────────────────────────────────────────────────────
@router.get("/intake", response_class=HTMLResponse)
def intake_list(request: Request, type_filter: str = None, status_filter: str = None,
                db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    q = db.query(IntakeRecord)
    if type_filter:   q = q.filter(IntakeRecord.intake_type == type_filter)
    if status_filter: q = q.filter(IntakeRecord.status == status_filter)
    records = q.order_by(IntakeRecord.created_at.desc()).all()

    enriched = []
    for r in records:
        p   = db.query(Person).filter(Person.id == r.person_id).first() if r.person_id else None
        ent = db.query(Entity).filter(Entity.id == r.entity_id).first() if r.entity_id else None
        enriched.append({"r": r, "person": p, "entity": ent})

    entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()
    return templates.TemplateResponse("pages/notifications/intake_list.html", _ctx({
        "request": request, "current_user": cu,
        "enriched": enriched, "entities": entities,
        "type_filter": type_filter or "", "status_filter": status_filter or "",
    }))


@router.get("/intake/new", response_class=HTMLResponse)
def intake_new_form(request: Request, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    from backend.modules.fleet.models import Vehicle
    entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()
    people   = db.query(Person).filter(Person.is_active == True).order_by(Person.last_name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.spz).all()
    return templates.TemplateResponse("pages/notifications/intake_new.html", _ctx({
        "request": request, "current_user": cu,
        "entities": entities, "people": people, "vehicles": vehicles,
    }))


@router.post("/intake/new")
def intake_create(intake_type: str = Form(...), title: str = Form(...),
                  entity_id: str = Form(None), vehicle_id: str = Form(None),
                  person_id: str = Form(None), body: str = Form(None),
                  source_ref: str = Form(None), payload_json: str = Form(None),
                  db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = IntakeRecord(intake_type=intake_type, title=title,
                     entity_id=entity_id or None, vehicle_id=vehicle_id or None,
                     person_id=person_id or None, body=body,
                     source_channel="manual", source_ref=source_ref,
                     payload_json=payload_json, status="new")
    db.add(r); db.commit()
    audit(db, "CREATE", "intake_record", r.id, cu.id, cu.email, detail=f"type={intake_type}")
    return RedirectResponse(f"/intake/{r.id}", status_code=303)


@router.get("/intake/{record_id}", response_class=HTMLResponse)
def intake_detail(record_id: str, request: Request, db: Session = Depends(get_db),
                  cu: CurrentUser = Depends(get_current_user)):
    from backend.modules.fleet.models import Vehicle
    r = db.query(IntakeRecord).filter(IntakeRecord.id == record_id).first()
    if not r: raise HTTPException(404)
    p   = db.query(Person).filter(Person.id == r.person_id).first() if r.person_id else None
    ent = db.query(Entity).filter(Entity.id == r.entity_id).first() if r.entity_id else None
    v   = db.query(Vehicle).filter(Vehicle.id == r.vehicle_id).first() if r.vehicle_id else None
    all_vehicles = db.query(Vehicle).order_by(Vehicle.spz).all()
    all_people   = db.query(Person).filter(Person.is_active == True).order_by(Person.last_name).all()
    all_entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()
    return templates.TemplateResponse("pages/notifications/intake_detail.html", _ctx({
        "request": request, "current_user": cu,
        "r": r, "person": p, "entity": ent, "vehicle": v,
        "all_vehicles": all_vehicles, "all_people": all_people, "all_entities": all_entities,
    }))


@router.post("/intake/{record_id}/review")
def intake_review(record_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = db.query(IntakeRecord).filter(IntakeRecord.id == record_id).first()
    if not r: raise HTTPException(404)
    r.status = "reviewed"; r.reviewed_at = datetime.utcnow(); r.reviewed_by = cu.email
    db.commit()
    audit(db, "REVIEW", "intake_record", r.id, cu.id, cu.email)
    return RedirectResponse(f"/intake/{record_id}", status_code=303)


@router.post("/intake/{record_id}/ignore")
def intake_ignore(record_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = db.query(IntakeRecord).filter(IntakeRecord.id == record_id).first()
    if not r: raise HTTPException(404)
    r.status = "ignored"
    db.commit()
    audit(db, "IGNORE", "intake_record", r.id, cu.id, cu.email)
    return RedirectResponse("/intake", status_code=303)


@router.post("/intake/{record_id}/convert/odometer")
def convert_odometer(record_id: str, vehicle_id: str = Form(...),
                     km: int = Form(...), reading_date: str = Form(...),
                     db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    from backend.modules.fleet.models import OdometerReading
    r = db.query(IntakeRecord).filter(IntakeRecord.id == record_id).first()
    if not r: raise HTTPException(404)
    odo = OdometerReading(vehicle_id=vehicle_id, km=km, reading_date=reading_date,
                          recorded_by_id=cu.person_id, notes=f"Converted from intake {record_id}")
    db.add(odo); db.flush()
    r.status = "converted"; r.converted_type = "odometer_reading"; r.converted_id = odo.id
    db.commit()
    audit(db, "CONVERT", "intake_record", r.id, cu.id, cu.email, detail=f"→odometer {odo.id}")
    return RedirectResponse(f"/intake/{record_id}", status_code=303)


@router.post("/intake/{record_id}/convert/fine")
def convert_fine(record_id: str, vehicle_id: str = Form(...),
                 driver_person_id: str = Form(None), entity_id: str = Form(None),
                 fine_date: str = Form(...), amount: float = Form(None),
                 reason: str = Form(None), due_date: str = Form(None),
                 db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    from backend.modules.fleet.models import TrafficFine
    r = db.query(IntakeRecord).filter(IntakeRecord.id == record_id).first()
    if not r: raise HTTPException(404)
    f = TrafficFine(vehicle_id=vehicle_id, driver_person_id=driver_person_id or None,
                    entity_id=entity_id or None, fine_date=fine_date, amount=amount,
                    reason=reason, due_date=due_date, status="open", created_by_id=cu.person_id)
    db.add(f); db.flush()
    r.status = "converted"; r.converted_type = "traffic_fine"; r.converted_id = f.id
    db.commit()
    audit(db, "CONVERT", "intake_record", r.id, cu.id, cu.email, detail=f"→traffic_fine {f.id}")
    return RedirectResponse(f"/intake/{record_id}", status_code=303)


@router.post("/intake/{record_id}/convert/claim")
def convert_claim(record_id: str, vehicle_id: str = Form(...),
                  driver_person_id: str = Form(None), entity_id: str = Form(None),
                  claim_date: str = Form(...), location: str = Form(None),
                  description: str = Form(None), amount_claimed: float = Form(None),
                  db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    from backend.modules.fleet.models import InsuranceClaim
    r = db.query(IntakeRecord).filter(IntakeRecord.id == record_id).first()
    if not r: raise HTTPException(404)
    c = InsuranceClaim(vehicle_id=vehicle_id, driver_person_id=driver_person_id or None,
                       entity_id=entity_id or None, claim_date=claim_date, location=location,
                       description=description or r.body, amount_claimed=amount_claimed,
                       status="open", created_by_id=cu.person_id)
    db.add(c); db.flush()
    r.status = "converted"; r.converted_type = "insurance_claim"; r.converted_id = c.id
    db.commit()
    audit(db, "CONVERT", "intake_record", r.id, cu.id, cu.email, detail=f"→insurance_claim {c.id}")
    return RedirectResponse(f"/intake/{record_id}", status_code=303)
