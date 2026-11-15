"""Do not use CurrentUser.roles: it discards role scopes and validity dates."""
import hashlib
import hmac
from datetime import date
from fastapi import HTTPException, Request
from backend.core.models.kernel import RoleAssignment, Entity
from backend.core.security.auth import get_token
from backend.config import get_settings

HR_ROLES = {'owner', 'admin', 'hr'}
PAYROLL_ROLES = {'owner', 'admin', 'finance'}


def value(item):
    return getattr(item, 'value', item)


def valid_role(role):
    today = date.today()
    try:
        return (not role.valid_from or date.fromisoformat(role.valid_from) <= today) and (not role.valid_to or date.fromisoformat(role.valid_to) >= today)
    except ValueError:
        return False


def roles_for(db, cu):
    return [r for r in db.query(RoleAssignment).filter_by(person_id=cu.person_id).all() if valid_role(r)]


def permitted(db, cu, entity, accepted):
    if getattr(cu, 'portal', False):
        return False
    for r in roles_for(db, cu):
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
        return hmac.new(get_settings().secret_key.encode(), f'hr-portal:{cu.id}:{token}'.encode(), hashlib.sha256).hexdigest()
    token = get_token(request)
    if not token:
        raise HTTPException(401, 'Přihlaste se do Nexusu.')
    return hmac.new(get_settings().secret_key.encode(), f'hr:{cu.id}:{token}'.encode(), hashlib.sha256).hexdigest()


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
