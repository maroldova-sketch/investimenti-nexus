"""Additive tables. Existing Person and Employment remain authoritative."""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now


class HRCase(Base):
    __tablename__ = 'hr_case'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employment_id: Mapped[str] = mapped_column(ForeignKey('employment.id'), index=True)
    open_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    request_key: Mapped[str] = mapped_column(String(100), unique=True)
    created_by: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(30), default='complete_existing')
    status: Mapped[str] = mapped_column(String(30), default='draft')
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    template_version: Mapped[str] = mapped_column(String(50))
    context: Mapped[dict] = mapped_column(JSON)
    draft: Mapped[dict] = mapped_column(JSON, default=dict)
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    requirements_confirmed: Mapped[bool] = mapped_column(default=False)
    current_revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    __mapper_args__ = {'version_id_col': version}


class HRSubmission(Base):
    __tablename__ = 'hr_submission'
    __table_args__ = (UniqueConstraint('case_id', 'revision'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey('hr_case.id'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    sha256: Mapped[str] = mapped_column(String(64))
    submitted_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class HRDecision(Base):
    __tablename__ = 'hr_decision'
    __table_args__ = (UniqueConstraint('case_id', 'request_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey('hr_case.id'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    request_key: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[str] = mapped_column(String(36))
    note: Mapped[str] = mapped_column(String(1200), default='')
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


HR_TABLES = [HRCase.__table__, HRSubmission.__table__, HRDecision.__table__]
