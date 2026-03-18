from sqlalchemy.orm import Session
from backend.core.models.kernel import Person
from backend.modules.fleet.models import Vehicle, FuelCard
from backend.modules.staging.normalize import normalize_phone, normalize_name

def match_person(db, norm_email, norm_phone, norm_name, company_hint):
    if norm_email:
        p = db.query(Person).filter(Person.email_work == norm_email).first()
        if not p: p = db.query(Person).filter(Person.email_personal == norm_email).first()
        if p: return p.id, "exact_email"
    if norm_phone:
        for p in db.query(Person).filter(Person.is_active == True).all():
            if p.phone and normalize_phone(p.phone) == norm_phone:
                return p.id, "exact_phone"
    if norm_name:
        for p in db.query(Person).filter(Person.is_active == True).all():
            if normalize_name(f"{p.first_name} {p.last_name}") == norm_name:
                return p.id, "exact_name"
    return None, None

def match_vehicle(db, vin, plate):
    if vin:
        v = db.query(Vehicle).filter(Vehicle.vin == vin).first()
        if v: return v.id
    if plate:
        v = db.query(Vehicle).filter(Vehicle.spz == plate).first()
        if v: return v.id
    return None

def match_fuel_card(db, card_last4, plate):
    if card_last4:
        c = db.query(FuelCard).filter(FuelCard.card_last4 == card_last4, FuelCard.is_active == True).first()
        if c: return c.vehicle_id, c.id
    if plate:
        v = db.query(Vehicle).filter(Vehicle.spz == plate).first()
        if v: return v.id, None
    return None, None
