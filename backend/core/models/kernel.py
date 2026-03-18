import uuid, enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

def _uuid() -> str: return str(uuid.uuid4())
def _now() -> datetime: return datetime.utcnow()

class NexusRole(str, enum.Enum):
    OWNER="owner"; ADMIN="admin"; MANAGER="manager"
    HR="hr"; FINANCE="finance"; FLEET_MANAGER="fleet_manager"; READONLY="readonly"

class ScopeType(str, enum.Enum):
    ALL="all"; DIVISION="division"; ENTITY="entity"

class EntityType(str, enum.Enum):
    COMPANY="company"; BRANCH="branch"; CLINIC="clinic"
    LAB="lab"; PROJECT="project"; HOLDING="holding"

class Person(Base):
    __tablename__ = "person"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    maiden_name: Mapped[str|None] = mapped_column(String(100))
    title_before: Mapped[str|None] = mapped_column(String(20))
    email_work: Mapped[str|None] = mapped_column(String(200))
    email_personal: Mapped[str|None] = mapped_column(String(200))
    phone: Mapped[str|None] = mapped_column(String(30))
    personal_id: Mapped[str|None] = mapped_column(String(20))
    address_permanent: Mapped[str|None] = mapped_column(Text)
    nationality: Mapped[str|None] = mapped_column(String(60))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    # HR extended fields
    birth_date: Mapped[str|None] = mapped_column(String(10))
    hire_date: Mapped[str|None] = mapped_column(String(10))
    birth_place: Mapped[str|None] = mapped_column(String(200))
    rod_cislo: Mapped[str|None] = mapped_column(String(20))
    bank_account: Mapped[str|None] = mapped_column(String(60))
    health_insurance: Mapped[str|None] = mapped_column(String(100))
    marital_status: Mapped[str|None] = mapped_column(String(40))
    education: Mapped[str|None] = mapped_column(Text)
    position: Mapped[str|None] = mapped_column(String(200))
    department: Mapped[str|None] = mapped_column(String(200))
    work_location: Mapped[str|None] = mapped_column(String(100))
    employment_type: Mapped[str|None] = mapped_column(String(200))
    source_holding: Mapped[str|None] = mapped_column(String(20))

    memberships: Mapped[list["EntityMembership"]] = relationship(back_populates="person")
    role_assignments: Mapped[list["RoleAssignment"]] = relationship(
        back_populates="person",
        foreign_keys="[RoleAssignment.person_id]"
    )
    user_account: Mapped["UserAccount|None"] = relationship(back_populates="person", uselist=False)

    @property
    def full_name(self) -> str:
        parts = [self.title_before, self.first_name, self.last_name]
        return " ".join(p for p in parts if p)

class Entity(Base):
    __tablename__ = "entity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    legal_name: Mapped[str|None] = mapped_column(String(300))
    ico: Mapped[str|None] = mapped_column(String(20))
    dic: Mapped[str|None] = mapped_column(String(20))
    entity_type: Mapped[str] = mapped_column(SAEnum(EntityType), default=EntityType.COMPANY)
    parent_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    address: Mapped[str|None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    division: Mapped[str|None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    memberships: Mapped[list["EntityMembership"]] = relationship(back_populates="entity")

class EntityMembership(Base):
    __tablename__ = "entity_membership"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"))
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"))
    position: Mapped[str|None] = mapped_column(String(100))
    valid_from: Mapped[str|None] = mapped_column(String(10))
    valid_to: Mapped[str|None] = mapped_column(String(10))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    person: Mapped["Person"] = relationship(back_populates="memberships")
    entity: Mapped["Entity"] = relationship(back_populates="memberships")

class RoleAssignment(Base):
    __tablename__ = "role_assignment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"))
    role: Mapped[str] = mapped_column(SAEnum(NexusRole))
    scope_type: Mapped[str] = mapped_column(SAEnum(ScopeType), default=ScopeType.ENTITY)
    scope_entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    valid_from: Mapped[str|None] = mapped_column(String(10))
    valid_to: Mapped[str|None] = mapped_column(String(10))
    granted_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    person: Mapped["Person"] = relationship(
        back_populates="role_assignments",
        foreign_keys=[person_id]
    )

class UserAccount(Base):
    __tablename__ = "user_account"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), unique=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime|None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    person: Mapped["Person"] = relationship(back_populates="user_account")

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    user_id: Mapped[str|None] = mapped_column(String(36))
    user_email: Mapped[str|None] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(50))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str|None] = mapped_column(String(36))
    entity_id: Mapped[str|None] = mapped_column(String(36))
    detail: Mapped[str|None] = mapped_column(Text)
    ip_address: Mapped[str|None] = mapped_column(String(45))
