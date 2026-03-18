"""
Employment — thin model linking Person to Entity with salary basis.
People module reuses Person/Entity from kernel.
"""
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Numeric, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now

class EmploymentType(str, enum.Enum):
    HPP = "HPP"
    DPP = "DPP"
    DPC = "DPČ"
    SZCO = "OSVČ"
    OTHER = "Jiné"

class EmploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"

class Employment(Base):
    __tablename__ = "employment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"), index=True)
    employment_type: Mapped[str] = mapped_column(SAEnum(EmploymentType), default=EmploymentType.HPP)
    status: Mapped[str] = mapped_column(SAEnum(EmploymentStatus), default=EmploymentStatus.ACTIVE)
    position: Mapped[str|None] = mapped_column(String(100))
    date_start: Mapped[str] = mapped_column(String(10))
    date_end: Mapped[str|None] = mapped_column(String(10))
    monthly_gross_kc: Mapped[float|None] = mapped_column(Numeric(10,2))
    hourly_rate_kc: Mapped[float|None] = mapped_column(Numeric(8,2))
    notes: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    person: Mapped["Person"] = relationship()
    entity: Mapped["Entity"] = relationship()

from backend.core.models.kernel import Person, Entity
