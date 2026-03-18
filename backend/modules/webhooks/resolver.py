"""
Wave 3.3 — Phone → Person → Vehicle resolver.
Primary identity for WhatsApp intake is E.164 phone number.
"""
import re
from datetime import date
from sqlalchemy.orm import Session
from backend.core.models.kernel import Person
from backend.modules.fleet.models import VehicleAssignment


def normalize_phone(raw: str) -> str:
    """Normalize any phone string to E.164 +420XXXXXXXXX format."""
    if not raw:
        return ""
    digits = re.sub(r"[^\d+]", "", raw.strip())
    if digits.startswith("+"):
        return digits
    if digits.startswith("420") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 9 and digits[0] in "67":
        return "+420" + digits
    return digits


def resolve_driver(phone_e164: str, db: Session) -> dict:
    """
    Resolve phone → person → vehicle.

    Returns:
        {
            person_id: str | None,
            vehicle_id: str | None,
            entity_id: str | None,
            resolution: "resolved" | "unresolved" | "ambiguous",
            unresolved_reason: str | None,
        }
    """
    result = {
        "person_id": None,
        "vehicle_id": None,
        "entity_id": None,
        "vehicle_resolution": "none",
        "unresolved_reason": None,
    }

    if not phone_e164:
        result["unresolved_reason"] = "no_phone"
        return result

    # 1. Find person by phone (normalized match)
    persons = db.query(Person).filter(Person.is_active == True).all()
    matched = [p for p in persons if normalize_phone(p.phone or "") == phone_e164]

    if not matched:
        result["unresolved_reason"] = f"phone_not_found:{phone_e164}"
        return result

    if len(matched) > 1:
        result["unresolved_reason"] = f"multiple_persons_for_phone:{phone_e164}"
        return result

    person = matched[0]
    result["person_id"] = person.id

    # 2. Find active vehicle assignment
    today = date.today().isoformat()
    assignments = db.query(VehicleAssignment).filter(
        VehicleAssignment.person_id == person.id,
        VehicleAssignment.date_from <= today,
    ).all()
    # Filter: date_to is None (open) or >= today
    active = [a for a in assignments if not a.date_to or a.date_to >= today]

    if len(active) == 0:
        result["vehicle_resolution"] = "none"
        result["unresolved_reason"] = "no_active_vehicle"
    elif len(active) == 1:
        a = active[0]
        result["vehicle_id"] = a.vehicle_id
        result["vehicle_resolution"] = "one"
        # Try to get entity from vehicle
        from backend.modules.fleet.models import Vehicle
        v = db.query(Vehicle).filter(Vehicle.id == a.vehicle_id).first()
        if v:
            result["entity_id"] = v.entity_id
    else:
        result["vehicle_resolution"] = "ambiguous"
        result["unresolved_reason"] = f"multiple_active_vehicles:{len(active)}"

    return result
