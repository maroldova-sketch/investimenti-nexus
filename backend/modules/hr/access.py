"""Do not use CurrentUser.roles: it discards role scopes and validity dates."""
import hashlib
import hmac
from datetime import date
from types import SimpleNamespace
from fastapi import HTTPException, Request
from sqlalchemy import String, select, type_coerce
from backend.core.models.kernel import RoleAssignment, Entity, NexusRole, ScopeType
from backend.core.security.auth import get_token
from backend.config import get_settings

HR_ROLES = {'owner', 'admin', 'hr'}
PAYROLL_ROLES = {'owner', 'admin', 'finance'}


def signing_key():
    from .startup import hr_signing_key
    return hr_signing_key(get_settings()).encode()


def value(item):
    return getattr(item, 'value', item)


def valid_role(role):
    today = date.today()
    try:
        return (not role.valid_from or date.fromisoformat(role.valid_from) <= today) and (not role.valid_to or date.fromisoformat(role.valid_to) >= today)
    except ValueError:
        return False


def enum_value(raw, enum):
    # Stored names may include values unknown to this release (e.g. a newer role);
    # read them as plain text so one unknown row cannot break authorization.
    if raw is None:
        return None
    raw = getattr(raw, 'value', raw)
    return enum[raw].value if raw in enum.__members__ else str(raw).lower()


def role_rows(db, person_id):
    t = RoleAssignment.__table__
    rows = db.execute(select(type_coerce(t.c.role, String), type_coerce(t.c.scope_type, String),
                             t.c.scope_entity_id, t.c.valid_from, t.c.valid_to)
                      .where(t.c.person_id == person_id)).all()
    found = [SimpleNamespace(role=enum_value(r[0], NexusRole), scope_type=enum_value(r[1], ScopeType),
                             scope_entity_id=r[2], valid_from=r[3], valid_to=r[4]) for r in rows]
    return [r for r in found if valid_role(r)]


def roles_for(db, cu):
    return role_rows(db, cu.person_id)


def permitted(db, cu, entity, accepted):
    if getattr(cu, 'portal', False):
        return False
    return holds_role(db, cu.person_id, entity, accepted)


def holds_role(db, person_id, entity, accepted):
    """Currently valid role of a specific person with a scope covering this entity."""
    if not person_id or entity is None:
        return False
    for r in role_rows(db, person_id):
        if value(r.role) not in accepted:
            continue
        scope = value(r.scope_type)
        if scope == 'all':
            return True
        if scope == 'entity' and r.scope_entity_id == entity.id:
            return True
        if scope == 'division' and r.scope_entity_id:
            anchor = db.get(Entity, r.scope_entity_id)
            if anchor and anchor.division and anchor.division == entity.division:
                return True
    return False


def csrf_token(request, cu):
    if getattr(cu, 'portal', False):
        token = request.cookies.get('hr_entry', '')
        return hmac.new(signing_key(), f'hr-portal:{cu.id}:{token}'.encode(), hashlib.sha256).hexdigest()
    token = get_token(request)
    if not token:
        raise HTTPException(401, 'Přihlaste se do Nexusu.')
    return hmac.new(signing_key(), f'hr:{cu.id}:{token}'.encode(), hashlib.sha256).hexdigest()


def check_csrf(request: Request, cu):
    if getattr(cu, 'portal', False):
        from .portal import check_portal_origin
        check_portal_origin(request, mutation=True)
    if not hmac.compare_digest(request.headers.get('x-hr-csrf', ''), csrf_token(request, cu)):
        raise HTTPException(403, 'Obnovte přihlášení před uložením.')
    origin = request.headers.get('origin')
    if origin:
        from urllib.parse import urlsplit
        if urlsplit(origin).netloc != request.headers.get('host'):
            raise HTTPException(403, 'Nepovolený původ požadavku.')
