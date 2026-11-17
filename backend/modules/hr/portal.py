"""Case-bound employee entry. It never creates a Nexus account or Nexus JWT."""
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import Field
from sqlalchemy.orm import Session
from backend.config import get_settings
from backend.core.models.base import get_db
from backend.core.security.auth import get_current_user
from backend.modules.people.models import Employment
from . import runtime
from .access import HR_ROLES, check_csrf, csrf_token, permitted, value, signing_key
from .audit import record
from .models import HRInvitation, HRCase
from .schema import StrictModel, VERSION, SECTIONS

router = APIRouter(tags=['hr-employee-entry'])


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class PortalActor:
    id: str
    person_id: str
    case_id: str
    session_hash: str
    portal: bool = True


class Issue(StrictModel):
    expected_version: int = Field(ge=1)
    request_key: str = Field(min_length=16, max_length=100)
    recipient_source: Literal['personal', 'work']
    confirmed: bool


class Revoke(StrictModel):
    expected_version: int = Field(ge=1)


class Ticket(StrictModel):
    token: str = Field(pattern=r'^[A-Za-z0-9_-]{43}$')


class Verify(Ticket):
    code: str = Field(pattern=r'^\d{8}$')


def check_portal_origin(request, mutation=False):
    try:
        origin = runtime.public_origin()
    except ValueError:
        raise HTTPException(503, 'Vstup zaměstnance ještě není nakonfigurovaný.')
    parsed = urlsplit(str(request.url))
    actual = parsed.scheme + '://' + parsed.netloc
    if actual != origin:
        raise HTTPException(403, 'Použijte zabezpečenou adresu z pozvánky.')
    if mutation and (request.headers.get('origin') != origin or request.headers.get('x-hr-portal') != '1'):
        raise HTTPException(403, 'Obnovte zabezpečenou stránku před pokračováním.')


def active_invitation(db, invitation):
    if (not invitation or invitation.revoked_at or invitation.expires_at <= now()
            or invitation.failed_attempts >= 20):
        raise HTTPException(401, 'Pozvánka již není platná. Požádejte HR o nový odkaz.')
    case = db.get(HRCase, invitation.case_id)
    employment = db.get(Employment, case.employment_id) if case else None
    if (not case or case.status == 'payroll_received' or not employment
            or (employment.person_id, employment.entity_id) != (case.context.get('person_id'), case.context.get('entity_id'))
            or not employment.person.is_active or not employment.entity.is_active
            or value(employment.status) == 'terminated'):
        raise HTTPException(401, 'Vstup k tomuto případu je uzavřen. Kontaktujte HR.')
    current_contact = employment.person.email_personal if invitation.recipient_source == 'personal' else employment.person.email_work
    if current_contact != invitation.recipient:
        raise HTTPException(401, 'Kontakt příjemce se změnil. HR musí připravit novou pozvánku.')
    return case, employment


def revalidate_actor(db, actor):
    invitation = db.get(HRInvitation, actor.id)
    case, employment = active_invitation(db, invitation)
    if (not invitation.session_hash or invitation.session_hash != actor.session_hash
            or not invitation.session_expires_at or invitation.session_expires_at <= now()
            or case.id != actor.case_id or employment.person_id != actor.person_id):
        raise HTTPException(401, 'Ověření vypršelo. Otevřete původní pozvánku a ověřte se znovu.')


def get_portal_actor(request: Request, db: Session = Depends(get_db)):
    check_portal_origin(request)
    token = request.cookies.get('hr_entry', '')
    if len(token) != 43:
        raise HTTPException(401, 'Nejprve ověřte vstup kódem z e-mailu.')
    hashed = digest(token)
    invitation = db.query(HRInvitation).filter_by(session_hash=hashed).first()
    case, employment = active_invitation(db, invitation)
    actor = PortalActor(invitation.id, employment.person_id, case.id, hashed)
    revalidate_actor(db, actor)
    return actor


def masked(email):
    local, domain = email.rsplit('@', 1)
    return local[:1] + '•••@' + domain


def invitation_info(invitation):
    return dict(id=invitation.id, recipient=masked(invitation.recipient),
                expires_at=invitation.expires_at.isoformat() + 'Z',
                revoked=bool(invitation.revoked_at), expired=invitation.expires_at <= now(),
                locked=invitation.failed_attempts >= 20)


@router.get('/api/hr/cases/{case_id}/invitations')
def list_invitations(case_id: str, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    from .routes import resolve
    case, employment = resolve(db, cu, case_id)
    if not permitted(db, cu, employment.entity, HR_ROLES):
        raise HTTPException(403, 'Pozvánky spravuje HR.')
    contacts = [{'source': source, 'address': address} for source, address in
                [('personal', employment.person.email_personal), ('work', employment.person.email_work)]
                if runtime.valid_email(address)]
    return dict(contacts=contacts, invitations=[invitation_info(i) for i in
                db.query(HRInvitation).filter_by(case_id=case.id).order_by(HRInvitation.created_at.desc()).all()])


@router.post('/api/hr/cases/{case_id}/invitations')
def issue(case_id: str, body: Issue, request: Request, cu=Depends(get_current_user), db: Session = Depends(get_db)):
    from .routes import resolve, check_version, editable, commit
    check_csrf(request, cu)
    case, employment = resolve(db, cu, case_id)
    if not permitted(db, cu, employment.entity, HR_ROLES):
        raise HTTPException(403, 'Pozvánky vytváří HR.')
    editable(case)
    if not runtime.invitations_ready():
        raise HTTPException(503, 'Pozvánky vyžadují zabezpečený portál a nakonfigurované doručování kódů.')
    address = employment.person.email_personal if body.recipient_source == 'personal' else employment.person.email_work
    if not body.confirmed or not runtime.valid_email(address):
        raise HTTPException(422, 'HR musí potvrdit ověřený e-mail příjemce v osobní kartě.')
    previous = db.query(HRInvitation).filter_by(request_key=body.request_key).first()
    if previous:
        if (previous.case_id, previous.created_by, previous.recipient) != (case.id, cu.id, address):
            raise HTTPException(409, 'Klíč požadavku již patří jiné pozvánce.')
        return dict(invitation=invitation_info(previous), url=None, case_version=case.version,
                    notice='Odkaz se zobrazuje jen při vytvoření. Pokud jste jej neuložili, vytvořte novou pozvánku.')
    check_version(case, body.expected_version)
    for old in db.query(HRInvitation).filter_by(active_key=case.id).all():
        old.revoked_at = now()
        old.active_key = None
        old.session_hash = None
    db.flush()
    token = secrets.token_urlsafe(32)
    invitation = HRInvitation(case_id=case.id, active_key=case.id, request_key=body.request_key,
                              token_hash=digest(token), recipient=address, recipient_source=body.recipient_source, created_by=cu.id,
                              expires_at=now() + timedelta(days=7))
    db.add(invitation)
    case.version += 1
    record(db, case.id, 'invitation_created', cu, recipient_source=body.recipient_source)
    commit(db)
    return dict(invitation=invitation_info(invitation), case_version=case.version,
                url=runtime.public_origin() + '/hr/entry#' + token,
                notice='Pozvánka je připravená ke sdílení. Ještě nebyla odeslána.')


@router.post('/api/hr/cases/{case_id}/invitations/{invitation_id}/revoke')
def revoke(case_id: str, invitation_id: str, body: Revoke, request: Request,
           cu=Depends(get_current_user), db: Session = Depends(get_db)):
    from .routes import resolve, check_version, commit
    check_csrf(request, cu)
    case, employment = resolve(db, cu, case_id)
    if not permitted(db, cu, employment.entity, HR_ROLES):
        raise HTTPException(403, 'Pozvánky spravuje HR.')
    invitation = db.get(HRInvitation, invitation_id)
    if not invitation or invitation.case_id != case.id:
        raise HTTPException(404, 'Pozvánka nebyla nalezena.')
    if not invitation.revoked_at:
        check_version(case, body.expected_version)
        invitation.revoked_at = now()
        invitation.active_key = None
        invitation.session_hash = None
        invitation.code_digest = None
        case.version += 1
        record(db, case.id, 'invitation_revoked', cu, invitation_id=invitation.id)
        commit(db)
    return dict(invitation=invitation_info(invitation), case_version=case.version)


@router.get('/hr/entry')
def entry(request: Request):
    check_portal_origin(request)
    return FileResponse(Path(__file__).resolve().parents[3] / 'frontend/static/hr/entry.html')


def find_ticket(db, token):
    invitation = db.query(HRInvitation).filter_by(token_hash=digest(token)).first()
    active_invitation(db, invitation)
    return invitation


def code_hash(invitation_id, nonce, code):
    return hmac.new(signing_key(), f'hr-code:{invitation_id}:{nonce}:{code}'.encode(), hashlib.sha256).hexdigest()


@router.post('/hr/api/code')
def request_code(body: Ticket, request: Request, db: Session = Depends(get_db)):
    from .routes import commit
    check_portal_origin(request, mutation=True)
    invitation = find_ticket(db, body.token)
    if invitation.sends >= 10 or (invitation.last_send_at and now() - invitation.last_send_at < timedelta(seconds=60)):
        raise HTTPException(429, 'Další kód lze vyžádat nejdříve za minutu. Při opakovaných potížích kontaktujte HR.')
    if not runtime.invitations_ready():
        raise HTTPException(503, 'Doručování kódu není dostupné. Kontaktujte HR.')
    code = f'{secrets.randbelow(100_000_000):08d}'
    nonce = secrets.token_hex(16)
    invitation.code_nonce = nonce
    invitation.code_digest = code_hash(invitation.id, nonce, code)
    invitation.code_expires_at = now() + timedelta(minutes=10)
    invitation.code_attempts = 0
    invitation.sends += 1
    invitation.last_send_at = now()
    actor = PortalActor(invitation.id, '', invitation.case_id, '')
    record(db, invitation.case_id, 'entry_code_requested', actor)
    commit(db)  # Reserve the rate limit before invoking the delivery adapter.
    try:
        reference = runtime.send_code(invitation.recipient, code)
    except Exception:
        db.refresh(invitation)
        if invitation.code_nonce == nonce:
            invitation.code_digest = None
            record(db, invitation.case_id, 'entry_delivery_failed', actor)
            commit(db)
        raise HTTPException(503, 'Kód se nepodařilo doručit. Za minutu to zkuste znovu nebo kontaktujte HR.')
    if reference:
        record(db, invitation.case_id, 'entry_code_handed_over', actor, delivery=reference)
        commit(db)
    return dict(recipient=masked(invitation.recipient), expires_in=600)


@router.post('/hr/api/verify')
def verify(body: Verify, request: Request, response: Response, db: Session = Depends(get_db)):
    from .routes import commit
    check_portal_origin(request, mutation=True)
    invitation = find_ticket(db, body.token)
    if (not invitation.code_digest or not invitation.code_expires_at or invitation.code_expires_at <= now()
            or invitation.code_attempts >= 5):
        raise HTTPException(401, 'Kód již neplatí. Vyžádejte nový kód.')
    actor = PortalActor(invitation.id, '', invitation.case_id, '')
    invitation.code_attempts += 1
    if not hmac.compare_digest(invitation.code_digest, code_hash(invitation.id, invitation.code_nonce, body.code)):
        invitation.failed_attempts += 1
        record(db, invitation.case_id, 'entry_code_failed', actor)
        commit(db)
        raise HTTPException(401, 'Kód nesouhlasí. Zkontrolujte poslední doručený kód.')
    token = secrets.token_urlsafe(32)
    invitation.session_hash = digest(token)
    invitation.session_expires_at = min(invitation.expires_at, now() + timedelta(hours=2))
    invitation.code_digest = None  # Single use; concurrent verification loses the SQL version race.
    record(db, invitation.case_id, 'entry_verified', actor)
    commit(db)
    response.set_cookie('hr_entry', token, max_age=7200, httponly=True, secure=True, samesite='strict', path='/hr')
    return dict(verified=True)


@router.get('/hr/api/meta')
def portal_meta(request: Request, actor=Depends(get_portal_actor)):
    return dict(template_version=VERSION, sections=SECTIONS, csrf=csrf_token(request, actor),
                case_id=actor.case_id, can_create=False,
                capabilities={'uploads': runtime.uploads_ready(), 'external_invitations': False, 'payroll_export': False},
                notice='Podklady jsou dostupné pouze vám a pověřeným personálním a mzdovým rolím.')


@router.post('/hr/api/logout')
def logout(request: Request, response: Response, actor=Depends(get_portal_actor), db: Session = Depends(get_db)):
    from .routes import commit
    check_csrf(request, actor)
    invitation = db.get(HRInvitation, actor.id)
    invitation.session_hash = None
    record(db, actor.case_id, 'entry_logout', actor)
    commit(db)
    response.delete_cookie('hr_entry', path='/hr', secure=True, httponly=True, samesite='strict')
    return dict(closed=True)


# Reuse the same domain operations with an explicit case-scoped actor. None of
# the HR/finance/listing endpoints are registered in the employee namespace.
from .routes import SaveDraft, Action, get_case, save, action
from .documents import Withdraw, upload, download, withdraw


@router.get('/hr/api/cases/{case_id}')
def portal_case(case_id: str, actor=Depends(get_portal_actor), db: Session = Depends(get_db)):
    return get_case(case_id, actor, db)


@router.put('/hr/api/cases/{case_id}/draft')
def portal_save(case_id: str, body: SaveDraft, request: Request,
                actor=Depends(get_portal_actor), db: Session = Depends(get_db)):
    return save(case_id, body, request, actor, db)


@router.post('/hr/api/cases/{case_id}/actions')
def portal_action(case_id: str, body: Action, request: Request,
                  actor=Depends(get_portal_actor), db: Session = Depends(get_db)):
    if body.action != 'submit':
        raise HTTPException(403, 'Zaměstnanec může podklady pouze odeslat ke kontrole.')
    return action(case_id, body, request, actor, db)


@router.post('/hr/api/cases/{case_id}/documents')
async def portal_upload(case_id: str, request: Request,
                        actor=Depends(get_portal_actor), db: Session = Depends(get_db)):
    return await upload(case_id, request, actor, db)


@router.get('/hr/api/cases/{case_id}/documents/{document_id}')
def portal_download(case_id: str, document_id: str, actor=Depends(get_portal_actor), db: Session = Depends(get_db)):
    return download(case_id, document_id, actor, db)


@router.post('/hr/api/cases/{case_id}/documents/{document_id}/withdraw')
def portal_withdraw(case_id: str, document_id: str, body: Withdraw, request: Request,
                     actor=Depends(get_portal_actor), db: Session = Depends(get_db)):
    return withdraw(case_id, document_id, body, request, actor, db)
