"""Wave 3.4 — Employment contract CRUD routes."""
import os, uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity, AuditLog
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from .contract_models import EmploymentContract

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(prefix="/people", tags=["contracts"])

CONTRACT_TYPES = [
    ("HPP",        "Hlavní pracovní poměr"),
    ("DPP",        "Dohoda o provedení práce"),
    ("DPC",        "Dohoda o pracovní činnosti"),
    ("OSVČ",       "OSVČ / fakturace"),
    ("JEDNATEL",   "Jednatel / statutár"),
    ("DOBROVOLNIK","Dobrovolník"),
]
SALARY_TYPES = [
    ("monthly",    "Měsíční paušál"),
    ("hourly",     "Hodinová sazba"),
    ("commission", "Provize"),
    ("fixed",      "Fixní odměna"),
]

def _ctx(d):
    d.setdefault("active_section", "people")
    d.setdefault("contract_types", CONTRACT_TYPES)
    d.setdefault("salary_types", SALARY_TYPES)
    return d


@router.get("/{person_id}/contracts", response_class=HTMLResponse)
def person_contracts(person_id: str, request: Request,
                     db: Session = Depends(get_db),
                     cu: CurrentUser = Depends(get_current_user)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        return RedirectResponse("/people")
    contracts = db.query(EmploymentContract).filter(
        EmploymentContract.person_id == person_id
    ).order_by(EmploymentContract.valid_from.desc().nullslast()).all()
    entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()
    return templates.TemplateResponse("pages/people/contracts.html", _ctx({
        "request": request, "current_user": cu,
        "person": person, "contracts": contracts, "entities": entities,
    }))


@router.post("/{person_id}/contracts/new")
def create_contract(
    person_id: str,
    entity_id: str = Form(...),
    contract_type: str = Form(...),
    position_title: str = Form(""),
    department: str = Form(""),
    work_location: str = Form(""),
    salary_type: str = Form("monthly"),
    salary_amount: str = Form(""),
    hourly_rate: str = Form(""),
    weekly_hours: str = Form(""),
    valid_from: str = Form(""),
    valid_to: str = Form(""),
    contract_number: str = Form(""),
    meal_voucher: str = Form("off"),
    meal_voucher_amount: str = Form(""),
    transport_allowance: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user),
):
    def _float(v):
        try: return float(v) if v.strip() else None
        except: return None

    c = EmploymentContract(
        id=str(uuid.uuid4()),
        person_id=person_id,
        entity_id=entity_id,
        contract_type=contract_type,
        position_title=position_title or None,
        department=department or None,
        work_location=work_location or None,
        salary_type=salary_type,
        salary_amount=_float(salary_amount),
        hourly_rate=_float(hourly_rate),
        weekly_hours=_float(weekly_hours),
        is_full_time=(float(weekly_hours) >= 35 if weekly_hours.strip() else True),
        valid_from=valid_from or None,
        valid_to=valid_to or None,
        contract_number=contract_number or None,
        meal_voucher=(meal_voucher == "on"),
        meal_voucher_amount=_float(meal_voucher_amount),
        transport_allowance=_float(transport_allowance),
        notes=notes or None,
        created_by=cu.email,
        is_active=True,
    )
    db.add(c)
    db.commit()
    audit(db, "CREATE", "employment_contract", c.id, cu.id, cu.email,
          detail=f"{contract_type} | {entity_id} | {salary_amount} Kč")
    return RedirectResponse(f"/people/{person_id}/contracts", status_code=303)


@router.post("/{person_id}/contracts/{contract_id}/deactivate")
def deactivate_contract(person_id: str, contract_id: str,
                        db: Session = Depends(get_db),
                        cu: CurrentUser = Depends(get_current_user)):
    c = db.query(EmploymentContract).filter(EmploymentContract.id == contract_id).first()
    if c:
        c.is_active = False
        db.commit()
        audit(db, "UPDATE", "employment_contract", contract_id, cu.id, cu.email,
              detail="deactivated")
    return RedirectResponse(f"/people/{person_id}/contracts", status_code=303)
