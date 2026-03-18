"""Wave 3.0 — Notification generators (deterministic, no AI, no cron)."""
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from .models import Notification, NotificationDelivery


def _exists(db: Session, related_type: str, related_id: str | None, title_prefix: str) -> bool:
    """Prevent duplicate notifications for same trigger."""
    return db.query(Notification).filter(
        Notification.related_type == related_type,
        Notification.related_id == related_id,
        Notification.status.in_(["new", "read", "acknowledged"]),
        Notification.title.like(f"{title_prefix}%"),
    ).first() is not None


def _create(db: Session, **kwargs) -> Notification:
    n = Notification(**kwargs)
    db.add(n)
    db.flush()  # ensure n.id is available before FK reference
    db.add(NotificationDelivery(notification_id=n.id, channel="in_app",
                                 delivery_status="sent", recipient="in_app"))
    return n


def generate_odometer_notifications(db: Session) -> int:
    """Flag active driver/vehicle pairs with no odometer in 45+ days."""
    from backend.modules.fleet.models import Vehicle, VehicleAssignment, OdometerReading
    cutoff = (date.today() - timedelta(days=45)).isoformat()
    assignments = db.query(VehicleAssignment).filter(
        VehicleAssignment.date_to == None
    ).all()
    count = 0
    for a in assignments:
        last = db.query(OdometerReading).filter(
            OdometerReading.vehicle_id == a.vehicle_id
        ).order_by(OdometerReading.reading_date.desc()).first()
        needs_reminder = not last or last.reading_date < cutoff
        if not needs_reminder:
            continue
        title = f"Chybí odečet tachometru"
        if _exists(db, "odometer", a.vehicle_id, title):
            continue
        _create(db, vehicle_id=a.vehicle_id, person_id=a.person_id,
                related_type="odometer", related_id=a.vehicle_id,
                title=title,
                body=f"Vozidlo {a.vehicle_id} — žádný odečet za posledních 45 dní.",
                severity="warn", status="new", target_scope="fleet_manager")
        count += 1
    db.commit()
    return count


def generate_compliance_notifications(db: Session) -> int:
    """Flag vehicles with STK or insurance expiring within 30 days."""
    from backend.modules.fleet.models import Vehicle
    today = date.today()
    warn_date = (today + timedelta(days=30)).isoformat()
    today_str = today.isoformat()
    count = 0
    for v in db.query(Vehicle).filter(Vehicle.status == "aktivní").all():
        # STK
        if v.stk_valid_to:
            if v.stk_valid_to <= today_str:
                title = f"STK prošlá"
                severity = "error"
            elif v.stk_valid_to <= warn_date:
                title = f"STK brzy vyprší"
                severity = "warn"
            else:
                title = None
            if title and not _exists(db, "compliance", v.id, title):
                _create(db, vehicle_id=v.id, related_type="compliance", related_id=v.id,
                        title=title, body=f"SPZ {v.spz} — STK do {v.stk_valid_to}.",
                        severity=severity, status="new", target_scope="fleet_manager")
                count += 1
    db.commit()
    return count


def generate_deduction_notifications(db: Session) -> int:
    """Flag deduction cases pending approval or approved but not exported."""
    from backend.modules.fleet.models import DeductionCase
    count = 0
    # Pending approval
    pending = db.query(DeductionCase).filter(
        DeductionCase.status.in_(["draft", "pending_approval"])
    ).all()
    for d in pending:
        title = "Srážka čeká na schválení"
        if not _exists(db, "deduction", d.id, title):
            _create(db, person_id=d.person_id, vehicle_id=d.vehicle_id,
                    entity_id=d.entity_id, related_type="deduction", related_id=d.id,
                    title=title, body=f"Typ: {d.case_type}, částka: {d.amount} Kč",
                    severity="warn", status="new", target_scope="manager")
            count += 1
    # Approved not exported
    approved = db.query(DeductionCase).filter(
        DeductionCase.status == "approved",
        DeductionCase.export_batch_id == None
    ).all()
    for d in approved:
        title = "Schválená srážka čeká na export"
        if not _exists(db, "deduction", d.id, title):
            _create(db, person_id=d.person_id, entity_id=d.entity_id,
                    related_type="deduction", related_id=d.id,
                    title=title, body=f"Typ: {d.case_type}, částka: {d.amount} Kč — připravit export.",
                    severity="info", status="new", target_scope="hr")
            count += 1
    db.commit()
    return count


def generate_fuel_review_notifications(db: Session) -> int:
    """Flag unresolved staged PHM rows with actual data."""
    from backend.modules.staging.models import StgFuelMonthly
    unresolved = db.query(StgFuelMonthly).filter(
        StgFuelMonthly.status == "unresolved",
        StgFuelMonthly.amount_total != None,
    ).all()
    if not unresolved:
        return 0
    title = f"Nevyřešené PHM záznamy"
    if _exists(db, "fuel", None, title):
        return 0
    _create(db, related_type="fuel",
            title=title,
            body=f"{len(unresolved)} nevyřešených PHM řádků v stagingu — zkontrolujte import.",
            severity="warn", status="new", target_scope="fleet_manager")
    db.commit()
    return 1
