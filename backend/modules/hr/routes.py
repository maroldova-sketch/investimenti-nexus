import hashlib
import json
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import IntegrityError
from pydantic import Field, ValidationError
from backend.core.models.base import get_db
from backend.core.security.auth import get_current_user
from backend.core.models.kernel import Person
from backend.modules.people.models import Employment
from .models import HRCase, HRSubmission, HRDecision
from .schema import (StrictModel, Requirement, VERSION, SECTIONS, AnswerError, default_requirements,
                     review_issues, template, suggested_requirements)
from .access import (HR_ROLES, PAYROLL_ROLES, permitted, roles_for, value, csrf_token, check_csrf,
                     holds_role)
from . import runtime
from .documents import manifest, validate_reference, Withdraw, upload, download, withdraw


def private_response(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'


router = APIRouter(tags=['hr-intake'], dependencies=[Depends(private_response)])


class CreateCase(StrictModel):
    employment_id: str = Field(min_length=1, max_length=36)
    kind: Literal['complete_existing', 'change'] = 'complete_existing'
    request_key: str = Field(min_length=16, max_length=100)
    hr_owner_id: str | None = Field(default=None, max_length=36)
    payroll_owner_id: str | None = Field(default=None, max_length=36)


class SaveDraft(StrictModel):
    expected_version: int = Field(ge=1)
    answers: dict
    confirm_clear: bool = False


class Owners(StrictModel):
    expected_version: int = Field(ge=1)
    hr_owner_id: str = Field(min_length=1, max_length=36)
    payroll_owner_id: str | None = Field(default=None, max_length=36)


PAYROLL_ATTESTATIONS = ['payroll_import', 'authority_filing']


class Action(StrictModel):
    expected_version: int = Field(ge=1)
    revision: int = Field(ge=0)
    request_key: str = Field(min_length=16, max_length=100)
    action: Literal['submit', 'return', 'review', 'payroll_return', 'payroll_receive', *PAYROLL_ATTESTATIONS]
    note: str = Field(default='', max_length=1200)
    confirmed: bool = False


class RequirementsUpdate(StrictModel):
    expected_version: int = Field(ge=1)
    items: list[Requirement] = Field(max_length=40)
    confirmed: bool


def commit(db):
    try:
        db.commit()
    except (StaleDataError, IntegrityError):
        db.rollback()
        raise HTTPException(409, 'Případ se mezitím změnil nebo už existuje. Obnovte jeho stav.')


def check_version(case, expected):
    if case.version != expected:
        raise HTTPException(409, 'Novější změna už byla uložena. Vaše údaje nebyly přepsány.')


def editable(case):
    if case.status not in ['draft', 'returned']:
        raise HTTPException(409, 'Odeslanou verzi nelze upravovat. HR ji může vrátit, po převzetí založte změnový případ.')


def case_template(case):
    try:
        return template(case.template_version)
    except KeyError:
        raise HTTPException(409, 'Tato verze formuláře vyžaduje vlastní validátor.')


def check_hr_owner(db, entity, person_id):
    if not person_id or not holds_role(db, person_id, entity, HR_ROLES):
        raise HTTPException(422, 'Odpovědné HR musí být osoba s platnou personální rolí pro tuto firmu.')


def check_payroll_owner(db, entity, person_id):
    # Only an explicit finance role counts; owner/admin rights never imitate an accountant.
    if person_id and not holds_role(db, person_id, entity, {'finance'}):
        raise HTTPException(422, 'Mzdová osoba musí mít platnou mzdovou (finance) roli pro tuto firmu.')


def person_name(db, person_id):
    person = db.get(Person, person_id) if person_id else None
    return person.full_name if person else None


def employment_context(e):
    return dict(person_id=e.person_id, entity_id=e.entity_id, employment_id=e.id,
                name=e.person.full_name, employer=e.entity.legal_name or e.entity.name,
                ico=e.entity.ico, position=e.position or 'Pozice k upřesnění',
                employment_type=value(e.employment_type), start=e.date_start)


def resolve(db, cu, case_id):
    if getattr(cu, 'portal', False):
        from .portal import revalidate_actor
        revalidate_actor(db, cu)
        if case_id != cu.case_id:
            raise HTTPException(404, 'Případ nebyl nalezen.')
    case = db.get(HRCase, case_id)
    if not case:
        raise HTTPException(404, 'Případ nebyl nalezen.')
    e = db.get(Employment, case.employment_id)
    if not e or (e.person_id, e.entity_id) != (case.context.get('person_id'), case.context.get('entity_id')):
        raise HTTPException(409, 'Vazba pracovního vztahu se změnila. Je nutná kontrola HR.')
    if e.person_id != cu.person_id and not permitted(db, cu, e.entity, HR_ROLES | PAYROLL_ROLES):
        raise HTTPException(404, 'Případ nebyl nalezen.')
    return case, e


def describe(db, cu, case, e, detail=False):
    portal = getattr(cu, 'portal', False)
    is_payroll_owner = bool(case.payroll_owner_id) and case.payroll_owner_id == cu.person_id and not portal
    result = dict(id=case.id, kind=case.kind, status=case.status, version=case.version,
                  context=case.context, template_version=case.template_version,
                  revision=case.current_revision, updated_at=case.updated_at.isoformat(),
                  owners=dict(hr=person_name(db, case.hr_owner_id), payroll=person_name(db, case.payroll_owner_id),
                              hr_id=case.hr_owner_id, payroll_id=case.payroll_owner_id),
                  permissions=dict(edit=e.person_id == cu.person_id or permitted(db, cu, e.entity, HR_ROLES),
                                   hr=permitted(db, cu, e.entity, HR_ROLES),
                                   payroll=permitted(db, cu, e.entity, PAYROLL_ROLES),
                                   payroll_owner=is_payroll_owner and holds_role(db, cu.person_id, e.entity, {'finance'})))
    if detail:
        from .terms import handover, latest_terms
        try:
            tpl = template(case.template_version)
            issues, hidden = tpl['issues'](case.draft), tpl['hidden'](case.draft)
            sections, review_flags = tpl['sections'], tpl['review_flags']
        except KeyError:
            issues, hidden, sections, review_flags = [], [], [], False
        result.update(answers=case.draft, requirements=case.requirements,
                      documents=manifest(db, case.id),
                      requirements_confirmed=case.requirements_confirmed,
                      sections=sections, review_flags=review_flags, hidden_answers=hidden,
                      handover=handover(db, e.id),
                      issues=issues,
                      history=[dict(action=x.action, revision=x.revision, note=x.note,
                                    at=x.created_at.isoformat(), actor_id=x.actor_id)
                               for x in db.query(HRDecision).filter_by(case_id=case.id).order_by(HRDecision.created_at).all()])
        if not portal and permitted(db, cu, e.entity, HR_ROLES | PAYROLL_ROLES):
            terms = latest_terms(db, e.id)
            result['terms'] = terms
            result['suggested_requirements'] = (suggested_requirements(case.draft, case.requirements, case.template_version)
                                                if case.template_version in (VERSION,) else [])
        if portal:
            result['owners'] = dict(hr=result['owners']['hr'])
            result['requirements'] = [{k: x[k] for k in ['id', 'label', 'status']} for x in case.requirements]
            result['history'] = [{k: v for k, v in x.items() if k != 'actor_id'} for x in result['history']]
            for item in result['history']:
                if item['action'] not in ['return', 'payroll_return']:
                    item['note'] = ''
    return result


@router.get('/people/hr')
def page(cu=Depends(get_current_user)):
    path = Path(__file__).resolve().parents[3] / 'frontend/static/hr/index.html'
    return FileResponse(path, headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


@router.get('/api/hr/meta')
def meta(request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    return dict(template_version=VERSION, sections=SECTIONS, csrf=csrf_token(request, cu),
                can_create=any(value(r.role) in HR_ROLES for r in roles_for(db, cu)),
                person_id=cu.person_id,
                capabilities={'uploads': runtime.uploads_ready(), 'external_invitations': runtime.link_invitations_ready(),
                              'email_invitations': runtime.invitations_ready(), 'payroll_export': True},
                notice='Sběr a kontrola podkladů. Soukromou pozvánku lze připravit i bez známého e-mailu zaměstnance.')


@router.get('/api/hr/employments')
def employments(cu=Depends(get_current_user), db: Session = Depends(get_db)):
    return [employment_context(e) for e in db.query(Employment).all()
            if permitted(db, cu, e.entity, HR_ROLES)]


@router.get('/api/hr/cases')
def cases(cu=Depends(get_current_user), db: Session = Depends(get_db)):
    found = []
    for case, e in db.query(HRCase, Employment).join(Employment, Employment.id == HRCase.employment_id).order_by(HRCase.updated_at.desc()).all():
        if (e.person_id, e.entity_id) != (case.context.get('person_id'), case.context.get('entity_id')):
            continue
        if e.person_id == cu.person_id or permitted(db, cu, e.entity, HR_ROLES | PAYROLL_ROLES):
            found.append(describe(db, cu, case, e))
    return found


@router.post('/api/hr/cases')
def create(body: CreateCase, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    check_csrf(request, cu)
    e = db.get(Employment, body.employment_id)
    if not e or not permitted(db, cu, e.entity, HR_ROLES):
        raise HTTPException(404, 'Pracovní vztah není dostupný.')
    if not e.entity.is_active or not e.person.is_active or value(e.status) == 'terminated':
        raise HTTPException(409, 'Vyberte aktivní pracovní vztah.')
    old = db.query(HRCase).filter_by(request_key=body.request_key).first()
    if old:
        if old.employment_id != e.id or old.kind != body.kind or old.created_by != cu.id:
            raise HTTPException(409, 'Klíč požadavku patří jinému případu.')
        return describe(db, cu, old, e, True)
    if db.query(HRCase).filter_by(open_key=e.id).first():
        raise HTTPException(409, 'Tento pracovní vztah už má otevřený případ.')
    hr_owner = body.hr_owner_id or cu.person_id
    check_hr_owner(db, e.entity, hr_owner)
    check_payroll_owner(db, e.entity, body.payroll_owner_id)
    case = HRCase(employment_id=e.id, open_key=e.id, request_key=body.request_key,
                  created_by=cu.id, kind=body.kind, template_version=VERSION,
                  hr_owner_id=hr_owner, payroll_owner_id=body.payroll_owner_id,
                  context=employment_context(e), draft=prefill(e.person), requirements=default_requirements())
    db.add(case)
    commit(db)
    return describe(db, cu, case, e, True)


def prefill(p):
    """Copy only simple, already recorded facts; nothing is inferred or guessed."""
    from .schema_v2 import valid_rc
    draft = {k: v.strip() for k, v in dict(
        title_before=p.title_before, first_name=p.first_name, last_name=p.last_name, maiden_name=p.maiden_name,
        birth_date=p.birth_date, birth_place=p.birth_place, citizenship=p.nationality,
        email=p.email_personal, phone=p.phone).items() if isinstance(v, str) and v.strip()}
    rc = (p.rod_cislo or p.personal_id or '').strip()
    if rc and valid_rc(rc):
        draft.update(personal_id_status='assigned', personal_id=rc)
    if (p.health_insurance or '').strip() in {'111', '201', '205', '207', '209', '211', '213'}:
        draft['health_insurer'] = p.health_insurance.strip()
    return draft


@router.put('/api/hr/cases/{case_id}/owners')
def owners(case_id: str, body: Owners, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    check_csrf(request, cu)
    case, e = resolve(db, cu, case_id)
    if not permitted(db, cu, e.entity, HR_ROLES):
        raise HTTPException(403, 'Odpovědné osoby určuje HR.')
    check_version(case, body.expected_version)
    if case.status == 'payroll_received':
        raise HTTPException(409, 'Převzatý případ už nelze předat jiné osobě.')
    check_hr_owner(db, e.entity, body.hr_owner_id)
    check_payroll_owner(db, e.entity, body.payroll_owner_id)
    case.hr_owner_id, case.payroll_owner_id = body.hr_owner_id, body.payroll_owner_id
    from .audit import record
    record(db, case.id, 'owners_changed', cu, hr=body.hr_owner_id, payroll=body.payroll_owner_id)
    commit(db)
    return describe(db, cu, case, e, True)


@router.get('/api/hr/cases/{case_id}')
def get_case(case_id: str, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    case, e = resolve(db, cu, case_id)
    return describe(db, cu, case, e, True)


def checked_answers(answers, complete=False, version=VERSION):
    try:
        return template(version)['normalize'](answers, complete)
    except AnswerError as exc:
        raise HTTPException(422, {'message': str(exc), 'fields': exc.errors})
    except (ValueError, ValidationError):
        raise HTTPException(422, 'Zkontrolujte formát podkladů.')


@router.put('/api/hr/cases/{case_id}/draft')
def save(case_id: str, body: SaveDraft, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    check_csrf(request, cu)
    case, e = resolve(db, cu, case_id)
    if e.person_id != cu.person_id and not permitted(db, cu, e.entity, HR_ROLES):
        raise HTTPException(403, 'Tato role neupravuje podání zaměstnance.')
    check_version(case, body.expected_version)
    editable(case)
    tpl = case_template(case)
    answers = checked_answers(body.answers, version=case.template_version)
    dropped = tpl['dropped_hidden'](case.draft, answers)
    if dropped and not body.confirm_clear:
        raise HTTPException(409, {'message': 'Uložení by smazalo skryté odpovědi z jiné volby. Potvrďte jejich vymazání.',
                                  'hidden': dropped})
    case.draft = answers
    commit(db)
    return describe(db, cu, case, e, True)


@router.put('/api/hr/cases/{case_id}/requirements')
def requirements(case_id: str, body: RequirementsUpdate, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    check_csrf(request, cu)
    case, e = resolve(db, cu, case_id)
    if not permitted(db, cu, e.entity, HR_ROLES):
        raise HTTPException(403, 'Požadavky určuje HR.')
    check_version(case, body.expected_version)
    if case.status in ['reviewed', 'payroll_received']:
        raise HTTPException(409, 'Po kontrole nejprve vraťte případ k opravě nebo založte změnový případ.')
    ids = [x.id for x in body.items]
    if len(set(ids)) != len(ids) or not body.items:
        raise HTTPException(422, 'Požadavky musí mít jedinečná ID a nesmějí být prázdné.')
    for item in body.items:
        validate_reference(db, case.id, item.evidence_ref)
        if item.status == 'verified' and not item.evidence_ref:
            raise HTTPException(422, 'Ověřený požadavek musí odkazovat na důkaz.')
        if item.status in ['not_applicable', 'deferred'] and not item.reason:
            raise HTTPException(422, 'Výjimka nebo odklad vyžaduje důvod.')
    case.requirements = [x.model_dump() for x in body.items]
    case.requirements_confirmed = body.confirmed
    commit(db)
    return describe(db, cu, case, e, True)


@router.post('/api/hr/cases/{case_id}/actions')
def action(case_id: str, body: Action, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    check_csrf(request, cu)
    case, e = resolve(db, cu, case_id)
    payroll_actions = ['payroll_return', 'payroll_receive', *PAYROLL_ATTESTATIONS]
    if body.action == 'submit':
        if e.person_id != cu.person_id and not permitted(db, cu, e.entity, HR_ROLES):
            raise HTTPException(403, 'Podání není dostupné pro tuto roli.')
    elif body.action in ['return', 'review'] and not permitted(db, cu, e.entity, HR_ROLES):
        raise HTTPException(403, 'Chybí odpovídající personální role.')
    elif body.action in payroll_actions and (
            getattr(cu, 'portal', False) or not case.payroll_owner_id or case.payroll_owner_id != cu.person_id
            or not holds_role(db, cu.person_id, e.entity, {'finance'})):
        raise HTTPException(403, 'Mzdové kroky provádí jen určená mzdová osoba s platnou mzdovou rolí. '
                                 'Bez ní případ zůstává připravený pro mzdy, ale nepřevzatý.')
    if body.action in ['review', *payroll_actions] and e.person_id == cu.person_id:
        raise HTTPException(403, 'Vlastní podklady musí převzít jiná pověřená osoba.')
    previous = db.query(HRDecision).filter_by(case_id=case.id, request_key=body.request_key).first()
    if previous:
        if (previous.actor_id != cu.id or previous.action != body.action or previous.note != body.note
                or previous.evidence.get('request_revision') != body.revision
                or previous.evidence.get('confirmed') != body.confirmed):
            raise HTTPException(409, 'Klíč požadavku už byl použit pro jiný krok.')
        return describe(db, cu, case, e, True)
    check_version(case, body.expected_version)
    if case.current_revision != body.revision:
        raise HTTPException(409, 'Rozhodnutí se týká jiné verze podání.')
    if body.action == 'submit':
        editable(case)
        tpl = case_template(case)
        if tpl['review_flags'] and not body.confirmed:
            raise HTTPException(422, 'Potvrďte, že odesíláte podklady ke kontrole (nejde o podpis smlouvy ani Prohlášení).')
        answers = checked_answers(case.draft, complete=True, version=case.template_version)
        snapshot = dict(answers=tpl['effective'](answers), context=case.context, template_version=case.template_version,
                        documents=manifest(db, case.id), issues=tpl['issues'](answers))
        digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        case.current_revision += 1
        db.add(HRSubmission(case_id=case.id, revision=case.current_revision, snapshot=snapshot,
                            sha256=digest, submitted_by=cu.id))
        case.draft = answers
        case.status = 'submitted'
    elif body.action == 'return':
        if case.status not in ['submitted', 'reviewed'] or not body.note.strip():
            raise HTTPException(409, 'Vrácení vyžaduje odeslaný případ a konkrétní důvod opravy.')
        case.status = 'returned'
    elif body.action == 'payroll_return':
        if case.status != 'reviewed' or not body.note.strip():
            raise HTTPException(409, 'Mzdová role vrací zkontrolovanou nepřevzatou verzi s konkrétním důvodem opravy.')
        case.status = 'returned'
    elif body.action == 'review':
        if case.status != 'submitted' or not body.confirmed or not case.requirements_confirmed:
            raise HTTPException(409, 'HR musí potvrdit kontrolu a rozsah požadavků.')
        blockers = [x['label'] for x in case.requirements if x['blocks_payroll'] and x['status'] not in ['verified', 'not_applicable']]
        if blockers:
            raise HTTPException(409, 'Chybí podklady nutné pro předání: ' + ', '.join(blockers))
        for item in case.requirements:
            validate_reference(db, case.id, item['evidence_ref'])
        case.status = 'reviewed'
    elif body.action == 'payroll_receive':
        if case.status != 'reviewed' or not body.confirmed:
            raise HTTPException(409, 'Převzetí vyžaduje zkontrolovanou konkrétní verzi.')
        case.status = 'payroll_received'
        case.open_key = None
    else:
        # Import into payroll software and an official filing are separate, later
        # attestations; neither is implied by receipt or by an export download.
        if case.status != 'payroll_received' or not body.confirmed or not body.note.strip():
            raise HTTPException(409, 'Import i úřední podání potvrzuje mzdová osoba po převzetí, s konkrétním údajem (produkt, číslo podání).')
        case.version += 1
    db.add(HRDecision(case_id=case.id, revision=case.current_revision, request_key=body.request_key,
                      action=body.action, actor_id=cu.id, note=body.note,
                      evidence={'requirements': case.requirements, 'confirmed': body.confirmed,
                                'request_revision': body.revision,
                                'actor_type': 'invitation' if getattr(cu, 'portal', False) else 'account'}))
    commit(db)
    return describe(db, cu, case, e, True)


@router.get('/api/hr/cases/{case_id}/submissions/{revision}')
def submission(case_id: str, revision: int, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    case, e = resolve(db, cu, case_id)
    row = db.query(HRSubmission).filter_by(case_id=case.id, revision=revision).first()
    if not row:
        raise HTTPException(404, 'Verze nebyla nalezena.')
    return dict(revision=row.revision, sha256=row.sha256, snapshot=row.snapshot, created_at=row.created_at.isoformat())


@router.post('/api/hr/cases/{case_id}/documents')
async def upload_document(case_id: str, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    return await upload(case_id, request, cu, db)


@router.get('/api/hr/cases/{case_id}/documents/{document_id}')
def download_document(case_id: str, document_id: str, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    return download(case_id, document_id, cu, db)


@router.post('/api/hr/cases/{case_id}/documents/{document_id}/withdraw')
def withdraw_document(case_id: str, document_id: str, body: Withdraw, request: Request,
                      cu=Depends(get_current_user), db: Session = Depends(get_db)):
    return withdraw(case_id, document_id, body, request, cu, db)


@router.get('/api/hr/cases/{case_id}/access-events')
def access_events(case_id: str, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    from .models import HREvent
    case, employment = resolve(db, cu, case_id)
    if not permitted(db, cu, employment.entity, HR_ROLES):
        raise HTTPException(403, 'Přístupový audit je určen pověřené HR roli.')
    return [dict(kind=e.kind, actor_id=e.actor_id, actor_type=e.actor_type,
                 details=e.details, at=e.created_at.isoformat() + 'Z')
            for e in db.query(HREvent).filter_by(case_id=case.id).order_by(HREvent.created_at).all()]
