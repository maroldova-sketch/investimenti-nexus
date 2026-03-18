from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now
import enum

# Python enums — application logic only, not stored as DB enum type
class PeriodStatus(str, enum.Enum):
    OPEN = "open"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    LOCKED = "locked"

class LeaveType(str, enum.Enum):
    VACATION = "dovolená"
    SICK = "nemoc"
    PERSONAL = "osobní"
    UNPAID = "neplacené"
    OTHER = "jiné"

class LeaveStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"

class ApprovalType(str, enum.Enum):
    ATTENDANCE = "attendance"
    LEAVE = "leave"

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class PayrollBatchStatus(str, enum.Enum):
    DRAFT = "draft"
    EXPORTED = "exported"

class AttendancePeriod(Base):
    __tablename__ = "attendance_period"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="open")   # plain string
    created_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    approved_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    locked_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    approved_at: Mapped[datetime|None] = mapped_column(DateTime)
    locked_at: Mapped[datetime|None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    submissions: Mapped[list["AttendanceSubmission"]] = relationship(back_populates="period")

    @property
    def label(self) -> str:
        return f"{self.year}/{self.month:02d}"

class AttendanceSubmission(Base):
    __tablename__ = "attendance_submission"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    period_id: Mapped[str] = mapped_column(String(36), ForeignKey("attendance_period.id"), index=True)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"))
    days_worked: Mapped[float|None] = mapped_column(Numeric(5,2))
    hours_worked: Mapped[float|None] = mapped_column(Numeric(6,2))
    days_vacation: Mapped[float|None] = mapped_column(Numeric(5,2))
    days_sick: Mapped[float|None] = mapped_column(Numeric(5,2))
    gross_salary: Mapped[float|None] = mapped_column(Numeric(10,2))
    note: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    period: Mapped["AttendancePeriod"] = relationship(back_populates="submissions")
    person: Mapped["Person"] = relationship(foreign_keys=[person_id])

class LeaveRequest(Base):
    __tablename__ = "leave_request"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"))
    leave_type: Mapped[str] = mapped_column(String(30), default="dovolená")   # plain string
    date_from: Mapped[str] = mapped_column(String(10))
    date_to: Mapped[str] = mapped_column(String(10))
    days: Mapped[float|None] = mapped_column(Numeric(5,2))
    reason: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="submitted")      # plain string
    approved_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    approved_at: Mapped[datetime|None] = mapped_column(DateTime)
    reject_reason: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    person: Mapped["Person"] = relationship(foreign_keys=[person_id])
    approver: Mapped["Person|None"] = relationship(foreign_keys=[approved_by_id])

class ApprovalCase(Base):
    __tablename__ = "approval_case"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_type: Mapped[str] = mapped_column(String(20))          # plain string
    ref_id: Mapped[str] = mapped_column(String(36))
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # plain string
    assigned_to_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    resolved_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    resolved_at: Mapped[datetime|None] = mapped_column(DateTime)
    note: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class PayrollExportBatch(Base):
    __tablename__ = "payroll_export_batch"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    period_id: Mapped[str] = mapped_column(String(36), ForeignKey("attendance_period.id"))
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")    # plain string
    row_count: Mapped[int|None] = mapped_column(Integer)
    file_path: Mapped[str|None] = mapped_column(String(300))
    exported_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    exported_at: Mapped[datetime|None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

from backend.core.models.kernel import Person, Entity
