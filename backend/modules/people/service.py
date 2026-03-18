from sqlalchemy.orm import Session, joinedload
from backend.core.models.kernel import Person, Entity, EntityMembership, RoleAssignment, UserAccount, NexusRole, ScopeType
from backend.modules.people.models import Employment
from backend.core.security.auth import hash_password
from backend.core.audit.log import audit
from backend.core.models.kernel import _uuid

def get_all_people(db: Session) -> list[Person]:
    return db.query(Person).filter(Person.is_active == True).order_by(Person.last_name, Person.first_name).all()

def get_person(db: Session, person_id: str) -> Person | None:
    return db.query(Person).filter(Person.id == person_id).first()

def create_person(db: Session, data: dict, actor_id: str = None, actor_email: str = None) -> Person:
    p = Person(**{k: v for k, v in data.items() if v})
    db.add(p)
    db.flush()
    audit(db, "CREATE", "person", p.id, actor_id, actor_email, detail=p.full_name)
    db.commit()
    db.refresh(p)
    return p

def update_person(db: Session, person_id: str, data: dict, actor_id: str = None, actor_email: str = None) -> Person:
    p = db.query(Person).filter(Person.id == person_id).first()
    for k, v in data.items():
        if hasattr(p, k):
            setattr(p, k, v or None)
    audit(db, "UPDATE", "person", person_id, actor_id, actor_email)
    db.commit()
    db.refresh(p)
    return p

def assign_membership(db: Session, person_id: str, entity_id: str, position: str = None,
                      valid_from: str = None, actor_id: str = None, actor_email: str = None):
    existing = db.query(EntityMembership).filter(
        EntityMembership.person_id == person_id,
        EntityMembership.entity_id == entity_id,
        EntityMembership.valid_to == None,
    ).first()
    if existing:
        return existing
    m = EntityMembership(person_id=person_id, entity_id=entity_id, position=position, valid_from=valid_from)
    db.add(m)
    audit(db, "CREATE", "entity_membership", person_id, actor_id, actor_email,
          entity_id=entity_id, detail=f"position={position}")
    db.commit()
    return m

def assign_role(db: Session, person_id: str, role: str, scope_type: str = "all",
                scope_entity_id: str = None, actor_id: str = None, actor_email: str = None):
    r = RoleAssignment(
        person_id=person_id,
        role=role,
        scope_type=scope_type,
        scope_entity_id=scope_entity_id or None,
        granted_by_id=actor_id,
    )
    db.add(r)
    audit(db, "CREATE", "role_assignment", person_id, actor_id, actor_email,
          detail=f"role={role} scope={scope_type}")
    db.commit()
    return r

def create_employment(db: Session, data: dict, actor_id: str = None, actor_email: str = None) -> Employment:
    e = Employment(**{k: v for k, v in data.items() if v})
    db.add(e)
    audit(db, "CREATE", "employment", data.get("person_id"), actor_id, actor_email)
    db.commit()
    db.refresh(e)
    return e

def get_person_memberships(db: Session, person_id: str):
    return db.query(EntityMembership).filter(EntityMembership.person_id == person_id).all()

def get_person_roles(db: Session, person_id: str):
    return db.query(RoleAssignment).filter(RoleAssignment.person_id == person_id).all()

def get_person_employments(db: Session, person_id: str):
    return db.query(Employment).filter(Employment.person_id == person_id).all()
