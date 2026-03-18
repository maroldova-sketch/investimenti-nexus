"""
NEXUS — People Calendar Module
Narozeniny, jmeniny, výročí nástupu, vlastní události holdingu.
Plain String statuses, no DB Enum.
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now


class PersonCalendarEvent(Base):
    """Recurring annual event tied to a person — birthday, nameday, work anniversary, etc."""
    __tablename__ = "person_calendar_event"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), index=True)
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    event_type: Mapped[str] = mapped_column(String(30))  # birthday / nameday / work_anniversary / custom
    day: Mapped[int] = mapped_column(Integer)    # 1–31
    month: Mapped[int] = mapped_column(Integer)  # 1–12
    year: Mapped[int|None] = mapped_column(Integer)  # base year (for anniversary count)
    label: Mapped[str|None] = mapped_column(String(200))  # override display label
    notes: Mapped[str|None] = mapped_column(Text)
    notify_days_before: Mapped[int] = mapped_column(Integer, default=7)  # reminder N days ahead
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    person: Mapped["Person"] = relationship(foreign_keys=[person_id])
    entity: Mapped["Entity|None"] = relationship(foreign_keys=[entity_id])


class HoldingCalendarEvent(Base):
    """One-off or recurring company/holding event — not person-specific."""
    __tablename__ = "holding_calendar_event"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    title: Mapped[str] = mapped_column(String(300))
    event_type: Mapped[str] = mapped_column(String(30))  # holiday / company / milestone / reminder / other
    event_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    end_date: Mapped[str|None] = mapped_column(String(10))
    recurrence: Mapped[str|None] = mapped_column(String(20))  # none / yearly / monthly
    description: Mapped[str|None] = mapped_column(Text)
    color: Mapped[str|None] = mapped_column(String(20))  # CSS color class hint
    notify_days_before: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str|None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    entity: Mapped["Entity|None"] = relationship(foreign_keys=[entity_id])


class CzechNameDay(Base):
    """Czech name day calendar — one entry per name per day."""
    __tablename__ = "czech_nameday"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    day: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(60), index=True)
    name_normalized: Mapped[str] = mapped_column(String(60), index=True)  # lowercase, no diacritics


from backend.core.models.kernel import Person, Entity
