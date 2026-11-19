"""Internal HR setup without a terminal: company → person → relationship → owners.

Every step writes to the existing Nexus tables (Entity, Person, Employment).
Nothing is created by an employee's questionnaire: a new relationship exists
only after HR records it explicitly with its evidence.
"""
import re
import unicodedata
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import Entity, Person, EntityMembership, AuditLog, RoleAssignment, EntityType
from backend.core.security.auth import get_current_user
from backend.modules.people.models import Employment, EmploymentType, EmploymentStatus
from .access import HR_ROLES, PAYROLL_ROLES, permitted, check_csrf, holds_role, roles_for
from .schema import StrictModel
from . import runtime

router = APIRouter(tags=['hr-wizard'])
TYPES = {'HPP': EmploymentType.HPP, 'DPP': EmploymentType.DPP, 'DPC': EmploymentType.DPC}


def audit(db, cu, action, resource_type, resource_id, entity_id, detail):
    db.add(AuditLog(user_id=cu.id, user_email=None, action=action, resource_type=resource_type,
                    resource_id=resource_id, entity_id=entity_id, detail=detail[:1000]))


def fold(text):
    text = unicodedata.normalize('NFKD', (text or '').strip().lower())
    return ''.join(c for c in text if not unicodedata.combining(c))


def masked(email):
    if not email or '@' not in email:
        return ''
    local, domain = email.rsplit('@', 1)
    return local[:1] + '•••@' + domain


def valid_ico(ico):
    if not re.fullmatch(r'\d{8}', ico or ''):
        return False
    total = sum(int(d) * w for d, w in zip(ico[:7], range(8, 1, -1)))
    check = (11 - total % 11) % 10
    return check == int(ico[7])


def global_scope(db, cu, roles):
    return any(r.role in roles and r.scope_type == 'all' for r in roles_for(db, cu))


def entity_for(db, cu, entity_id, roles=HR_ROLES):
    entity = db.get(Entity, entity_id)
    if not entity or not entity.is_active or not permitted(db, cu, entity, roles):
        raise HTTPException(404, 'Firma není dostupná pro vaši roli.')
    return entity


def entities_of(db, person_id):
    ids = {e.entity_id for e in db.query(Employment).filter_by(person_id=person_id).all()}
    ids |= {m.entity_id for m in db.query(EntityMembership).filter_by(person_id=person_id).all()}
    return [db.get(Entity, i) for i in ids if i]


def visible_person(db, cu, person):
    return global_scope(db, cu, HR_ROLES) or any(permitted(db, cu, e, HR_ROLES) for e in entities_of(db, person.id) if e)


def person_view(db, person, entity=None):
    employments = db.query(Employment).filter_by(person_id=person.id).all()
    return dict(id=person.id, name=person.full_name, birth_year=(person.birth_date or '')[:4],
                active=person.is_active,
                contacts=[c for c in [dict(source='personal', address=person.email_personal),
                                      dict(source='work', address=person.email_work)]
                          if runtime.valid_email(c['address'])],
                employments=[dict(id=e.id, entity=e.entity.name, entity_id=e.entity_id,
                                  type=getattr(e.employment_type, 'value', e.employment_type),
                                  status=getattr(e.status, 'value', e.status), position=e.position or '',
                                  start=e.date_start, end=e.date_end)
                             for e in employments if entity is None or e.entity_id == entity.id])


class NewEntity(StrictModel):
    legal_name: str = Field(min_length=3, max_length=300)
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(pattern=r'^[A-Z0-9-]{2,20}$')
    ico: str = Field(pattern=r'^\d{8}$')
    division: str = Field(default='', max_length=50)
    address: str = Field(default='', max_length=500)
    source: str = Field(min_length=3, max_length=300)


class NewPerson(StrictModel):
    request_key: str = Field(min_length=16, max_length=100)
    entity_id: str = Field(min_length=1, max_length=36)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    title_before: str = Field(default='', max_length=20)
    birth_date: str = Field(default='', max_length=10)
    confirm_new: bool = False


class Contact(StrictModel):
    entity_id: str = Field(min_length=1, max_length=36)
    source: Literal['personal', 'work']
    email: str = Field(min_length=3, max_length=254)
    verification: str = Field(min_length=5, max_length=300)
    confirmed: bool


class NewEmployment(StrictModel):
    entity_id: str = Field(min_length=1, max_length=36)
    person_id: str = Field(min_length=1, max_length=36)
    employment_type: Literal['HPP', 'DPP', 'DPC']
    position: str = Field(min_length=2, max_length=100)
    date_start: str = Field(min_length=10, max_length=10)
    evidence: str = Field(min_length=5, max_length=500)
    confirmed: bool


@router.get('/api/hr/wizard/entities')
def entities(cu=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = [e for e in db.query(Entity).filter_by(is_active=True).order_by(Entity.name).all()
            if permitted(db, cu, e, HR_ROLES)]
    return dict(can_create=global_scope(db, cu, {'owner', 'admin'}),
                entities=[dict(id=e.id, name=e.name, legal_name=e.legal_name or '', ico=e.ico or '',
                               division=e.division or '', type=getattr(e.entity_type, 'value', e.entity_type))
                          for e in rows])


@router.post('/api/hr/wizard/entities')
def create_entity(body: NewEntity, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    check_csrf(request, cu)
    if not global_scope(db, cu, {'owner', 'admin'}):
        raise HTTPException(403, 'Novou firmu zakládá vlastník nebo správce Nexusu.')
    if not valid_ico(body.ico):
        raise HTTPException(422, 'IČO nemá platný kontrolní součet.')
    existing = db.query(Entity).filter(or_(Entity.ico == body.ico, Entity.code == body.code)).first()
    if existing:
        raise HTTPException(409, f'Firma už existuje: {existing.name} ({existing.code}). Použijte ji.')
    entity = Entity(code=body.code, name=body.name.strip(), legal_name=body.legal_name.strip(), ico=body.ico,
                    entity_type=EntityType.COMPANY, division=body.division.strip() or None,
                    address=body.address.strip() or None, is_active=True)
    db.add(entity)
    db.flush()
    audit(db, cu, 'hr_entity_created', 'entity', entity.id, entity.id, 'Zdroj: ' + body.source)
    db.commit()
    return dict(id=entity.id)


@router.get('/api/hr/wizard/people')
def people(entity_id: str, q: str = '', cu=Depends(get_current_user), db: Session = Depends(get_db)):
    entity = entity_for(db, cu, entity_id)
    linked = {e.person_id for e in db.query(Employment).filter_by(entity_id=entity.id).all()}
    linked |= {m.person_id for m in db.query(EntityMembership).filter_by(entity_id=entity.id).all()}
    found, hidden = {}, 0
    for pid in linked:
        person = db.get(Person, pid)
        if person:
            found[pid] = person
    needle = fold(q)
    if len(needle) >= 3:
        found = {k: v for k, v in found.items() if needle in fold(v.full_name) or needle in fold(v.email_work or '')
                 or needle in fold(v.email_personal or '')}
        like = f'%{q.strip()}%'
        for person in db.query(Person).filter(or_(Person.last_name.ilike(like), Person.first_name.ilike(like),
                                                  Person.email_work.ilike(like), Person.email_personal.ilike(like))).limit(50):
            if person.id in found:
                continue
            if visible_person(db, cu, person):
                found[person.id] = person
            else:
                hidden += 1
    return dict(people=[person_view(db, p) for p in sorted(found.values(), key=lambda p: fold(p.last_name))][:100],
                hidden_matches=hidden)


@router.post('/api/hr/wizard/people')
def create_person(body: NewPerson, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    check_csrf(request, cu)
    entity = entity_for(db, cu, body.entity_id)
    if body.birth_date:
        try:
            if date.fromisoformat(body.birth_date) > date.today():
                raise ValueError
        except ValueError:
            raise HTTPException(422, 'Zkontrolujte datum narození.')
    marker = 'request:' + body.request_key
    previous = db.query(AuditLog).filter_by(action='hr_person_created', user_id=cu.id, detail=marker).first()
    if previous:
        return dict(person=person_view(db, db.get(Person, previous.resource_id)))
    first, last = body.first_name.strip(), body.last_name.strip()
    same = [p for p in db.query(Person).filter(func.lower(Person.last_name) == last.lower()).all()
            if fold(p.first_name) == fold(first) and (not body.birth_date or not p.birth_date or p.birth_date == body.birth_date)]
    if same and not body.confirm_new:
        visible = [person_view(db, p) for p in same if visible_person(db, cu, p)]
        raise HTTPException(409, {'message': 'Osoba se stejným jménem už v evidenci je. Vyberte ji, '
                                             'nebo potvrďte, že jde o jiného člověka.',
                                  'matches': visible, 'hidden_matches': len(same) - len(visible)})
    person = Person(first_name=first, last_name=last, title_before=body.title_before.strip() or None,
                    birth_date=body.birth_date or None, is_active=True)
    db.add(person)
    db.flush()
    audit(db, cu, 'hr_person_created', 'person', person.id, entity.id, marker)
    db.commit()
    return dict(person=person_view(db, person))


@router.put('/api/hr/wizard/people/{person_id}/contact')
def confirm_contact(person_id: str, body: Contact, request: Request, cu=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Store a verified address on the person record (the only invitation source)."""
    check_csrf(request, cu)
    entity = entity_for(db, cu, body.entity_id)
    person = db.get(Person, person_id)
    if not person or not db.query(Employment).filter_by(person_id=person_id, entity_id=entity.id).first():
        raise HTTPException(404, 'Kontakt lze potvrdit jen u osoby s pracovním vztahem k této firmě.')
    email = body.email.strip()
    if not body.confirmed or not runtime.valid_email(email):
        raise HTTPException(422, 'Potvrďte ověřený e-mail zaměstnance.')
    clash = db.query(Person).filter(Person.id != person.id, or_(func.lower(Person.email_work) == email.lower(),
                                                                func.lower(Person.email_personal) == email.lower())).first()
    if clash:
        raise HTTPException(409, 'Tento e-mail už patří jiné osobě v evidenci. Ověřte totožnost.')
    if body.source == 'personal':
        person.email_personal = email
    else:
        person.email_work = email
    audit(db, cu, 'hr_contact_confirmed', 'person', person.id, entity.id,
          f'{body.source}: {masked(email)}; ověření: {body.verification.strip()}')
    db.commit()
    return dict(person=person_view(db, person, entity))


@router.post('/api/hr/wizard/employments')
def create_employment(body: NewEmployment, request: Request, cu=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    check_csrf(request, cu)
    entity = entity_for(db, cu, body.entity_id)
    person = db.get(Person, body.person_id)
    if not person or not person.is_active:
        raise HTTPException(404, 'Osoba není dostupná.')
    if not body.confirmed:
        raise HTTPException(422, 'Potvrďte, že vztah je doložen smlouvou nebo dohodou.')
    try:
        date.fromisoformat(body.date_start)
    except ValueError:
        raise HTTPException(422, 'Zkontrolujte datum vzniku vztahu.')
    kind = TYPES[body.employment_type]
    same = db.query(Employment).filter_by(person_id=person.id, entity_id=entity.id, employment_type=kind,
                                          date_start=body.date_start).first()
    if same:
        return dict(employment_id=same.id, existing=True)
    employment = Employment(person_id=person.id, entity_id=entity.id, employment_type=kind,
                            status=EmploymentStatus.ACTIVE, position=body.position.strip(),
                            date_start=body.date_start, notes='Založeno v HR průvodci; doklad: ' + body.evidence.strip())
    db.add(employment)
    db.flush()
    audit(db, cu, 'hr_employment_created', 'employment', employment.id, entity.id, 'Doklad: ' + body.evidence.strip())
    db.commit()
    return dict(employment_id=employment.id, existing=False)


@router.get('/api/hr/wizard/staff')
def staff(entity_id: str, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    entity = entity_for(db, cu, entity_id, HR_ROLES | PAYROLL_ROLES)
    ids = {row[0] for row in db.query(RoleAssignment.person_id).distinct().all()}
    hr, payroll = [], []
    for pid in ids:
        person = db.get(Person, pid)
        if not person or not person.is_active:
            continue
        if holds_role(db, pid, entity, HR_ROLES):
            hr.append(dict(id=pid, name=person.full_name))
        if holds_role(db, pid, entity, {'finance'}):
            payroll.append(dict(id=pid, name=person.full_name))
    return dict(hr=sorted(hr, key=lambda x: fold(x['name'])), payroll=sorted(payroll, key=lambda x: fold(x['name'])))
