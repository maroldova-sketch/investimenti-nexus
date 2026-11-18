"""Small audited command surface over the existing fleet tables.

No startup migrations, finance writes, messages or external service accounts.
The P0 release is restricted to a currently valid holding-wide owner/admin/
fleet_manager mandate. Employee and company-scoped access are not implied.
"""
import hashlib
import hmac
import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, inspect, select, type_coerce, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.config import get_settings
from backend.core.models.base import Base, get_db
from backend.core.models.kernel import AuditLog, Person, RoleAssignment, UserAccount
from backend.core.security.auth import CurrentUser, get_current_user, get_token
from .models import FleetEvent, FleetEventType, OdometerReading, Vehicle, VehicleAssignment

PRAGUE = ZoneInfo('Europe/Prague')


class FleetCommand(Base):
    __tablename__ = 'fleet_command'
    __table_args__ = (UniqueConstraint('actor_id', 'request_key', name='uq_fleet_command_actor_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey('user_account.id'))
    request_key: Mapped[str] = mapped_column(String(36))
    payload_hash: Mapped[str] = mapped_column(String(64))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey('vehicle.id'), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    record_id: Mapped[str] = mapped_column(String(36))
    effective_at: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(20))
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


FLEET_COMMAND_TABLES = [FleetCommand.__table__]


def today():
    return datetime.now(PRAGUE).date()


def valid_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Expected YYYY-MM-DD')
    return date.fromisoformat(value)


def require_manager(db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    # Read enum columns as raw strings: an unknown legacy role cannot grant access.
    t = RoleAssignment.__table__
    account = db.get(UserAccount, cu.id)
    person = db.get(Person, cu.person_id) if cu.person_id else None
    if not account or not account.is_active or account.person_id != cu.person_id or not person or not person.is_active:
        raise HTTPException(403, 'Neplatný uživatelský účet.')
    rows = db.execute(select(type_coerce(t.c.role, String), type_coerce(t.c.scope_type, String),
                             t.c.scope_entity_id, t.c.valid_from, t.c.valid_to)
                      .where(t.c.person_id == cu.person_id)).all()
    for role, scope, entity, start, end in rows:
        try:
            if start and valid_day(start) > today():
                continue
            if end and valid_day(end) < today():
                continue
            if start and end and valid_day(start) > valid_day(end):
                continue
        except ValueError:
            continue
        if str(role).lower() in {'owner', 'admin', 'fleet_manager'} and str(scope).lower() == 'all' and entity is None:
            return cu
    raise HTTPException(403, 'Tato verze vyžaduje platný holdingový mandát správce vozového parku.')


def legacy_readonly(request: Request, cu=Depends(require_manager)):
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        raise HTTPException(409, 'V pilotu zapisujte kilometry a závady přes Vozový park / Provoz. Ostatní změny zatím nejsou zapnuté.')
    return cu


def csrf_token(request, cu):
    token = get_token(request)
    if not token:
        raise HTTPException(401, 'Přihlaste se do Nexusu.')
    key = get_settings().secret_key.encode()
    return hmac.new(key, f'fleet:{cu.id}:{token}'.encode(), hashlib.sha256).hexdigest()


def check_csrf(request, cu):
    from urllib.parse import urlsplit
    origin = request.headers.get('origin')
    if origin and urlsplit(origin).netloc != request.headers.get('host'):
        raise HTTPException(403, 'Nepovolený původ požadavku.')
    if not hmac.compare_digest(request.headers.get('x-fleet-csrf', ''), csrf_token(request, cu)):
        raise HTTPException(403, 'Obnovte přihlášení před uložením.')


def validate_schema(engine):
    inspector = inspect(engine)
    required = {'vehicle', 'vehicle_assignment', 'odometer_reading', 'fleet_event', 'audit_log',
                'person', 'user_account', 'role_assignment', 'fleet_command'}
    if not required.issubset(set(inspector.get_table_names())):
        raise RuntimeError('Fleet schema is not installed; run the explicit additive migration after backup.')
    columns = {c['name'] for c in inspector.get_columns('fleet_command')}
    if not set(FleetCommand.__table__.columns.keys()).issubset(columns):
        raise RuntimeError('Fleet schema is incompatible.')
    uniques = inspector.get_unique_constraints('fleet_command')
    if not any(set(u['column_names']) == {'actor_id', 'request_key'} for u in uniques):
        raise RuntimeError('Fleet schema is missing its idempotency constraint.')


class CommandInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    vehicle_id: str = Field(min_length=1, max_length=36)
    expected_revision: str = Field(min_length=1, max_length=40)
    idempotency_key: uuid.UUID
    kind: Literal['odometer', 'defect']
    effective_at: AwareDatetime
    source: Literal['web', 'elias']
    km: int | None = Field(default=None, ge=0, le=9999999, strict=True)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator('effective_at', mode='before')
    @classmethod
    def explicit_timestamp(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value):
            raise ValueError('Čas musí být ISO timestamp s explicitním časovým posunem.')
        return value

    @model_validator(mode='after')
    def matching_fields(self):
        if self.kind == 'odometer' and (self.km is None or self.description is not None):
            raise ValueError('Odečet vyžaduje km a neobsahuje popis závady.')
        if self.kind == 'defect':
            if self.km is not None or not self.description or not self.description.strip():
                raise ValueError('Závada vyžaduje popis a neobsahuje odečet km.')
            self.description = self.description.strip()
        return self


def revision(vehicle):
    return vehicle.updated_at.isoformat(timespec='microseconds') if vehicle.updated_at else 'unknown'


def summary(vehicle):
    return dict(id=vehicle.id, spz=vehicle.spz, make=vehicle.make, model=vehicle.model,
                status=getattr(vehicle.status, 'value', vehicle.status), revision=revision(vehicle),
                km_current=vehicle.km_current, entity_id=vehicle.entity_id)


def load_vehicle(db, vehicle_id):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, 'Vozidlo nenalezeno.')
    return vehicle


def command_result(command):
    return json.loads(command.result_json)


def replay(db, cu, key, digest):
    previous = db.query(FleetCommand).filter_by(actor_id=cu.id, request_key=key).first()
    if previous:
        if not hmac.compare_digest(previous.payload_hash, digest):
            raise HTTPException(409, 'Stejný klíč už byl použit pro jiný požadavek.')
        return command_result(previous)
    return None


def execute(db, cu, body):
    payload = body.model_dump(mode='json')
    payload['effective_at'] = body.effective_at.astimezone(timezone.utc).isoformat()
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    key = str(body.idempotency_key)
    previous = replay(db, cu, key, digest)
    if previous:
        return previous
    vehicle = load_vehicle(db, body.vehicle_id)
    if revision(vehicle) == 'unknown' or revision(vehicle) != body.expected_revision:
        raise HTTPException(409, 'Karta vozidla se změnila. Načtěte ji znovu.')
    now = datetime.now(timezone.utc)
    if body.effective_at > now:
        raise HTTPException(422, 'Čas odečtu nebo závady nesmí být v budoucnosti.')
    day = body.effective_at.astimezone(PRAGUE).date().isoformat()
    # Lock the existing aggregate with compare-and-swap before checking its readings.
    changed_at = datetime.utcnow()
    old_updated_at = vehicle.updated_at
    acquired = db.execute(update(Vehicle).where(Vehicle.id == vehicle.id, Vehicle.updated_at == old_updated_at)
                          .values(updated_at=changed_at).execution_options(synchronize_session=False))
    if acquired.rowcount != 1:
        raise HTTPException(409, 'Souběžná změna vozidla. Načtěte kartu znovu.')
    record_id = str(uuid.uuid4())
    if body.kind == 'odometer':
        readings = db.query(OdometerReading).filter_by(vehicle_id=vehicle.id).all()
        for row in readings:
            try:
                valid_day(row.reading_date)
            except ValueError:
                raise HTTPException(409, 'Historie obsahuje neplatné datum odečtu; správce musí opravit podklady.')
            if row.reading_date == day:
                raise HTTPException(409, 'Tento den už má odečet. Oprava vyžaduje samostatné posouzení.')
            if (row.reading_date < day and row.km > body.km) or (row.reading_date > day and row.km < body.km):
                raise HTTPException(409, 'Odečet odporuje historii tachometru. Opravu nebo výměnu tachometru řešte samostatně.')
        # A legacy current value has no measurement date; do not silently overwrite it backwards.
        newest = not readings or day > max(row.reading_date for row in readings)
        if newest and vehicle.km_current is not None and body.km < vehicle.km_current:
            raise HTTPException(409, 'Odečet je nižší než dosud evidované kilometry.')
        db.add(OdometerReading(id=record_id, vehicle_id=vehicle.id, km=body.km,
                              reading_date=day, recorded_by_id=cu.person_id,
                              notes=f'{body.source}; effective_at={payload["effective_at"]}'))
        if newest:
            db.execute(update(Vehicle).where(Vehicle.id == vehicle.id).values(km_current=body.km, updated_at=changed_at)
                       .execution_options(synchronize_session=False))
    else:
        db.add(FleetEvent(id=record_id, vehicle_id=vehicle.id, event_type=FleetEventType.OTHER,
                          event_date=day, description='Závada: ' + body.description, created_by_id=cu.person_id))
    result = dict(id=str(uuid.uuid4()), vehicle_id=vehicle.id, record_id=record_id, kind=body.kind,
                  revision=changed_at.isoformat(timespec='microseconds'), effective_at=payload['effective_at'], status='recorded')
    result.update(record_date=day, km=body.km, description=body.description)
    db.add(FleetCommand(id=result['id'], actor_id=cu.id, request_key=key, payload_hash=digest,
                        vehicle_id=vehicle.id, kind=body.kind, record_id=record_id,
                        effective_at=result['effective_at'], source=body.source,
                        result_json=json.dumps(result, ensure_ascii=False)))
    db.add(AuditLog(user_id=cu.id, user_email=cu.email, action='CREATE', resource_type='fleet_command',
                    resource_id=result['id'], entity_id=vehicle.entity_id,
                    detail=json.dumps(dict(kind=body.kind, record_id=record_id, vehicle_id=vehicle.id,
                                           effective_at=result['effective_at'], source=body.source, request_key=key))))
    db.commit()
    return result


router = APIRouter(tags=['fleet-elias'], dependencies=[Depends(require_manager)])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[3] / 'frontend' / 'templates'))


@router.get('/fleet/operations')
def operations(request: Request, cu=Depends(require_manager)):
    return templates.TemplateResponse('pages/fleet/operations.html', dict(request=request, current_user=cu,
                                                                        active_section='fleet', page_title='Vozový park – provoz'))


@router.get('/api/fleet/elias/meta')
def meta(request: Request, cu=Depends(require_manager)):
    import os
    return dict(csrf=csrf_token(request, cu), release=os.environ.get('NEXUS_RELEASE_SHA') or 'unknown',
                capabilities=['vehicles.read', 'odometer.create', 'defect.create'], scope='holding-manager-only')


@router.get('/api/fleet/elias/vehicles')
def vehicles(q: str = Query(default='', max_length=100), db: Session = Depends(get_db)):
    # Small holding fleet: literal matching avoids SQL wildcard ambiguities.
    term = q.strip().casefold()
    rows = db.query(Vehicle).order_by(Vehicle.spz, Vehicle.id).all()
    return dict(items=[summary(v) for v in rows if not term or any(term in (getattr(v, k) or '').casefold()
                for k in ['id', 'spz', 'vin', 'make', 'model'])], observed_at=datetime.now(timezone.utc).isoformat())


@router.get('/api/fleet/elias/vehicles/{vehicle_id}')
def vehicle_detail(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = load_vehicle(db, vehicle_id)
    data = summary(vehicle)
    current, warning = [], False
    for row in db.query(VehicleAssignment).filter_by(vehicle_id=vehicle.id).all():
        try:
            start = valid_day(row.date_from)
            end = valid_day(row.date_to) if row.date_to else date.max
            if end < start:
                raise ValueError('reversed')
            if start <= today() <= end:
                current.append(row)
        except ValueError:
            warning = True
    warning = warning or len(current) > 1
    driver = db.get(Person, current[0].person_id) if len(current) == 1 and not warning else None
    data.update(current_driver=driver.full_name if driver else None, assignment_warning=warning,
                odometer_readings=[dict(id=r.id, km=r.km, reading_date=r.reading_date) for r in
                                   db.query(OdometerReading).filter_by(vehicle_id=vehicle.id).order_by(OdometerReading.reading_date.desc()).all()],
                events=[dict(id=e.id, event_date=e.event_date, description=e.description, event_type=getattr(e.event_type, 'value', e.event_type)) for e in
                        db.query(FleetEvent).filter_by(vehicle_id=vehicle.id).order_by(FleetEvent.event_date.desc()).limit(50).all()])
    return data


@router.post('/api/fleet/elias/commands')
def post_command(body: CommandInput, request: Request, db: Session = Depends(get_db), cu=Depends(require_manager)):
    check_csrf(request, cu)
    try:
        return execute(db, cu, body)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        # The actor/key winner can be recovered using the exact same request.
        raise HTTPException(409, 'Souběžný zápis. Zopakujte tentýž požadavek se stejným klíčem.')
    except OperationalError:
        db.rollback()
        raise HTTPException(503, 'Databáze je dočasně nedostupná. Ověřte výsledek opakováním stejného požadavku.')
    except Exception:
        db.rollback()
        raise


@router.get('/api/fleet/elias/commands/{command_id}')
def read_command(command_id: str, db: Session = Depends(get_db), cu=Depends(require_manager)):
    command = db.query(FleetCommand).filter_by(id=command_id, actor_id=cu.id).first()
    if not command:
        raise HTTPException(404, 'Záznam nenalezen.')
    cls = OdometerReading if command.kind == 'odometer' else FleetEvent
    record = db.get(cls, command.record_id)
    if not record or record.vehicle_id != command.vehicle_id:
        raise HTTPException(409, 'Původní zápis se nepodařilo ověřit.')
    result = command_result(command)
    valid = (record.km == result.get('km') and record.reading_date == result.get('record_date')
             and record.notes == f'{command.source}; effective_at={command.effective_at}') if command.kind == 'odometer' else (
                 record.description == 'Závada: ' + (result.get('description') or '')
                 and record.event_date == result.get('record_date') and record.event_type == FleetEventType.OTHER)
    if not valid:
        raise HTTPException(409, 'Obsah původního zápisu se změnil; vyžaduje ověření správcem.')
    return result
