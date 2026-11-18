from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import Entity, Person
from backend.core.security.auth import get_current_user, CurrentUser
from .models import Vehicle
from .periods import approved_attributions, decimal_total, transaction_period
import os


templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates"))
router = APIRouter(prefix="/fleet/phm", tags=["phm"])


def _totals(records):
    transactions = [r.transaction for r in records]
    return {"txn": len(transactions), "kc": decimal_total(transactions, "amount_total"),
            "litry": decimal_total(transactions, "liters_total"),
            "missing_amount": sum(t.amount_total is None for t in transactions)}


def _months(records):
    groups = {}
    for record in records:
        try:
            first, _ = transaction_period(record.transaction)
            key = first.year, first.month
        except (ValueError, TypeError):
            key = 0, 0
        groups.setdefault(key, []).append(record)
    result = []
    for (year, month), rows in sorted(groups.items()):
        result.append({"yr": year, "mo": month,
                       "label": f"{month:02d}/{year}" if year else "Neplatné / neznámé období",
                       **_totals(rows), "transactions": [
                           {"id": r.transaction.id, "datum": r.transaction.transaction_date,
                            "lit": r.transaction.liters_total, "kc": r.transaction.amount_total,
                            "vendor": r.transaction.vendor_name or "—", "ref": r.transaction.source_doc_ref or "—",
                            "reason": r.reason} for r in rows]})
    return result


def _vehicle_data(db, entity=None):
    vehicles = {v.id: v for v in db.query(Vehicle).all()}
    entities = {e.id: e.code for e in db.query(Entity).all()}
    people = {p.id: p.full_name for p in db.query(Person).all()}
    grouped = {}
    for record in approved_attributions(db):
        v = vehicles.get(record.transaction.vehicle_id)
        code = entities.get(v.entity_id, "Neurčena") if v else "Neurčena"
        if entity and code != entity:
            continue
        grouped.setdefault(record.transaction.vehicle_id, []).append(record)
    result = []
    for vid, rows in grouped.items():
        vehicle = vehicles.get(vid)
        drivers = {}
        for row in rows:
            drivers.setdefault(row.person_id, []).append(row)
        result.append({"veh_id": vid, "spz": vehicle.spz or "—" if vehicle else "Neznámé vozidlo",
                       "vozidlo": vehicle.display_name if vehicle else vid,
                       "entita": entities.get(vehicle.entity_id, "Neurčena") if vehicle else "Neurčena",
                       **_totals(rows), "drivers": [
                           {"person_id": pid, "ridic": people.get(pid, "Neznámá osoba") if pid else "K ověření — nepřiřazeno řidiči",
                            **_totals(items), "months": _months(items)} for pid, items in drivers.items()]})
    return sorted(result, key=lambda row: row["kc"], reverse=True)


def _person_data(db, entity=None):
    result = {}
    for vehicle in _vehicle_data(db, entity):
        for driver in vehicle["drivers"]:
            pid = driver["person_id"]
            person = result.setdefault(pid, {"person_id": pid, "ridic": driver["ridic"], "vehicles": [],
                                            "txn": 0, "kc": 0, "litry": 0, "missing_amount": 0})
            person["vehicles"].append({**{k: vehicle[k] for k in ("veh_id", "spz", "vozidlo", "entita")},
                                       **{k: driver[k] for k in ("txn", "kc", "litry", "missing_amount", "months")}})
            for key in ("txn", "kc", "litry", "missing_amount"):
                person[key] += driver[key]
    return sorted(result.values(), key=lambda row: row["kc"], reverse=True)


@router.get("", response_class=HTMLResponse)
def phm_overview(request: Request, view: str = "vozidla", entity: str = None,
                 db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    view = "lide" if view == "lide" else "vozidla"
    data = _person_data(db, entity) if view == "lide" else _vehicle_data(db, entity)
    entities = db.query(Entity.code).order_by(Entity.code).all()
    return templates.TemplateResponse("pages/fleet/phm2.html", {
        "request": request, "current_user": current_user, "data": data, "view": view,
        "entity": entity, "total_kc": sum(d["kc"] for d in data),
        "total_lit": sum(d["litry"] for d in data), "total_txn": sum(d["txn"] for d in data),
        "missing_amount": sum(d["missing_amount"] for d in data), "entities": [e[0] for e in entities],
    })
