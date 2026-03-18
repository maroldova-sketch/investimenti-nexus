from sqlalchemy.orm import Session
from backend.core.models.kernel import AuditLog
from datetime import datetime

def audit(db: Session, action: str, resource_type: str, resource_id: str = None,
          user_id: str = None, user_email: str = None, entity_id: str = None,
          detail: str = None, ip: str = None):
    entry = AuditLog(
        timestamp=datetime.utcnow(),
        user_id=user_id,
        user_email=user_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip,
    )
    db.add(entry)
    db.commit()
