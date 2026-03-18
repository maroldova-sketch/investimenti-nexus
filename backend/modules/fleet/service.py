from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from .models import Vehicle, VehicleAssignment, FuelTransactionStaging, FleetEvent, FuelCard, FuelTransaction
from backend.core.models.kernel import Person
from datetime import date

def get_all_vehicles(db: Session) -> list[Vehicle]:
    return db.query(Vehicle).options(
        joinedload(Vehicle.assignments).joinedload(VehicleAssignment.person),
        joinedload(Vehicle.fuel_cards),
        joinedload(Vehicle.events),
    ).order_by(Vehicle.make, Vehicle.model).all()

def get_vehicle(db: Session, vehicle_id: str) -> Vehicle | None:
    return db.query(Vehicle).options(
        joinedload(Vehicle.assignments).joinedload(VehicleAssignment.person),
        joinedload(Vehicle.fuel_cards),
        joinedload(Vehicle.events),
        joinedload(Vehicle.odometer_readings),
        joinedload(Vehicle.fuel_transactions).joinedload(FuelTransactionStaging.person),
    ).filter(Vehicle.id == vehicle_id).first()

def get_phm_summary(db: Session, period: str = None) -> dict:
    """Legacy: from FuelTransactionStaging."""
    q = db.query(FuelTransactionStaging)
    if period:
        q = q.filter(FuelTransactionStaging.period == period)
    txns = q.all()
    return {
        "total_kc": sum((t.price_inc_vat or 0) for t in txns),
        "total_litres": sum((t.litres or 0) for t in txns),
        "count": len(txns),
    }

def get_canonical_phm_summary(db: Session, month: int = None, year: int = None) -> dict:
    """PHM from canonical FuelTransaction table."""
    q = db.query(FuelTransaction).filter(FuelTransaction.status == "approved")
    if month: q = q.filter(FuelTransaction.month == month)
    if year:  q = q.filter(FuelTransaction.year == year)
    txns = q.all()
    return {
        "total_kc":     sum((float(t.amount_total) if t.amount_total else 0) for t in txns),
        "total_litres": sum((float(t.liters_total) if t.liters_total else 0) for t in txns),
        "count":        len(txns),
    }

def get_canonical_phm_by_vehicle(db: Session, vehicle_id: str) -> list:
    return db.query(FuelTransaction).filter(
        FuelTransaction.vehicle_id == vehicle_id,
        FuelTransaction.status == "approved",
    ).order_by(FuelTransaction.year.desc(), FuelTransaction.month.desc()).all()

def get_top_phm_vehicles(db: Session, month: int = None, year: int = None, limit: int = 5) -> list:
    """Top vehicles by PHM cost from canonical table."""
    q = db.query(
        FuelTransaction.vehicle_id,
        func.sum(FuelTransaction.amount_total).label("total_kc"),
        func.sum(FuelTransaction.liters_total).label("total_litres"),
        func.count(FuelTransaction.id).label("tx_count"),
    ).filter(FuelTransaction.status == "approved")
    if month: q = q.filter(FuelTransaction.month == month)
    if year:  q = q.filter(FuelTransaction.year == year)
    rows = q.group_by(FuelTransaction.vehicle_id).order_by(
        func.sum(FuelTransaction.amount_total).desc()
    ).limit(limit).all()

    result = []
    for r in rows:
        v = db.query(Vehicle).filter(Vehicle.id == r.vehicle_id).first()
        result.append({
            "vehicle": v,
            "total_kc": float(r.total_kc or 0),
            "total_litres": float(r.total_litres or 0),
            "tx_count": r.tx_count,
        })
    return result

def get_phm_by_vehicle(db: Session, vehicle_id: str, period: str = None):
    q = db.query(FuelTransactionStaging).filter(
        FuelTransactionStaging.vehicle_id == vehicle_id
    )
    if period:
        q = q.filter(FuelTransactionStaging.period == period)
    return q.order_by(FuelTransactionStaging.period.desc()).all()

def get_stk_alerts(db: Session) -> list[Vehicle]:
    today = date.today().isoformat()
    return db.query(Vehicle).filter(
        Vehicle.stk_valid_to != None,
        Vehicle.stk_valid_to < today,
        Vehicle.status == "aktivní",
    ).all()

def add_phm_transaction(db: Session, data: dict) -> FuelTransactionStaging:
    t = FuelTransactionStaging(**data)
    db.add(t); db.commit(); db.refresh(t)
    return t

def log_event(db: Session, vehicle_id: str, event_type: str, date_str: str,
              description: str = None, cost_kc: int = None, user_id: str = None):
    ev = FleetEvent(vehicle_id=vehicle_id, event_type=event_type, event_date=date_str,
                    description=description, cost_kc=cost_kc, created_by_id=user_id)
    db.add(ev); db.commit(); db.refresh(ev)
    return ev

def change_driver(db: Session, vehicle_id: str, new_person_id: str,
                  date_from: str, reason: str = None, changed_by_id: str = None):
    current = db.query(VehicleAssignment).filter(
        VehicleAssignment.vehicle_id == vehicle_id,
        VehicleAssignment.date_to == None,
    ).first()
    if current:
        current.date_to = date_from
    new_asgn = VehicleAssignment(vehicle_id=vehicle_id, person_id=new_person_id,
                                  date_from=date_from, reason=reason)
    db.add(new_asgn); db.commit()
    return new_asgn
