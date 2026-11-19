"""Internal HR context of an employment relationship (append-only revisions).

Contract, employer-side workplace, working time, pay, equipment, benefits and a
car belong to HR. The employee never orders or edits them; the employee portal
receives only the names of items already handed over, for clarification.
"""
from datetime import date
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import AfterValidator, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.security.auth import get_current_user
from backend.modules.people.models import Employment
from .access import HR_ROLES, PAYROLL_ROLES, permitted, check_csrf
from .models import HRTerms
from .schema import StrictModel

router = APIRouter(tags=['hr-terms'])


def iso_date(value):
    if value:
        date.fromisoformat(value)
    return value


DateText = Annotated[str, Field(default='', max_length=10), AfterValidator(iso_date)]


class Equipment(StrictModel):
    item: str = Field(min_length=1, max_length=200)
    handed_over_on: DateText = ''
    evidence_ref: str = Field(default='', max_length=300)


class Benefit(StrictModel):
    benefit: str = Field(min_length=1, max_length=200)
    since: DateText = ''
    note: str = Field(default='', max_length=300)


class Car(StrictModel):
    assigned: Literal['no', 'yes', 'review'] = 'no'
    vehicle: str = Field(default='', max_length=200)
    private_use: Literal['', 'yes', 'no', 'review'] = ''
    since: DateText = ''


class TermsData(StrictModel):
    contract_signed_on: DateText = ''
    contract_ref: str = Field(default='', max_length=300)
    workplace: str = Field(default='', max_length=300)
    fte: str = Field(default='', max_length=20, pattern=r'^$|^(0(\.\d{1,3})?|1(\.0{1,3})?)$')
    weekly_hours: str = Field(default='', max_length=6, pattern=r'^$|^\d{1,2}(\.\d)?$')
    schedule: Literal['', 'fixed', 'flexible', 'shift', 'uneven', 'review'] = ''
    pay_type: Literal['', 'monthly', 'hourly', 'agreement', 'review'] = ''
    pay_amount: str = Field(default='', max_length=20, pattern=r'^$|^\d{1,9}([.,]\d{1,2})?$')
    pay_note: str = Field(default='', max_length=500)
    probation_until: DateText = ''
    fixed_term_until: DateText = ''
    equipment: list[Equipment] = Field(default_factory=list, max_length=40)
    benefits: list[Benefit] = Field(default_factory=list, max_length=40)
    car: Car = Field(default_factory=Car)
    note: str = Field(default='', max_length=1000)


class TermsUpdate(StrictModel):
    expected_revision: int = Field(ge=0)
    effective_from: Annotated[str, Field(min_length=10, max_length=10), AfterValidator(iso_date)]
    source: str = Field(min_length=3, max_length=300)
    data: TermsData


def latest_row(db, employment_id):
    return (db.query(HRTerms).filter_by(employment_id=employment_id)
            .order_by(HRTerms.revision.desc()).first())


def serialize(row):
    if not row:
        return None
    return dict(revision=row.revision, effective_from=row.effective_from, data=row.data,
                source=row.source, created_by=row.created_by, created_at=row.created_at.isoformat())


def latest_terms(db, employment_id):
    return serialize(latest_row(db, employment_id))


def handover(db, employment_id):
    """Names only: what the employee already has and may clarify."""
    row = latest_row(db, employment_id)
    if not row:
        return dict(equipment=[], benefits=[], car=None)
    data = row.data or {}
    car = data.get('car') or {}
    return dict(equipment=[x['item'] for x in data.get('equipment', [])],
                benefits=[x['benefit'] for x in data.get('benefits', [])],
                car=car.get('vehicle') or 'Přidělené vozidlo' if car.get('assigned') == 'yes' else None)


def employment_for(db, cu, employment_id, roles):
    e = db.get(Employment, employment_id)
    if not e or not permitted(db, cu, e.entity, roles):
        raise HTTPException(404, 'Pracovní vztah není dostupný.')
    return e


@router.get('/api/hr/employments/{employment_id}/terms')
def get_terms(employment_id: str, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    employment_for(db, cu, employment_id, HR_ROLES | PAYROLL_ROLES)
    return dict(current=latest_terms(db, employment_id),
                history=[serialize(r) for r in db.query(HRTerms).filter_by(employment_id=employment_id)
                         .order_by(HRTerms.revision.desc()).limit(20).all()])


@router.post('/api/hr/employments/{employment_id}/terms')
def add_terms(employment_id: str, body: TermsUpdate, request: Request,
              cu=Depends(get_current_user), db: Session = Depends(get_db)):
    check_csrf(request, cu)
    employment_for(db, cu, employment_id, HR_ROLES)
    current = db.query(func.max(HRTerms.revision)).filter_by(employment_id=employment_id).scalar() or 0
    if current != body.expected_revision:
        raise HTTPException(409, 'Interní kontext mezitím změnil někdo jiný. Obnovte ho; nic nebylo přepsáno.')
    db.add(HRTerms(employment_id=employment_id, revision=current + 1, effective_from=body.effective_from,
                   data=body.data.model_dump(), source=body.source.strip(), created_by=cu.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Interní kontext mezitím změnil někdo jiný. Obnovte ho; nic nebylo přepsáno.')
    return get_terms(employment_id, cu, db)
