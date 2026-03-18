"""Wave 3.0 — Notification + Intake models. Plain String statuses throughout."""
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now


class Notification(Base):
    __tablename__ = "notification"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    vehicle_id: Mapped[str|None] = mapped_column(String(36))  # no FK — soft ref
    related_type: Mapped[str|None] = mapped_column(String(30))   # odometer/fine/claim/deduction/fuel/compliance/general
    related_id: Mapped[str|None] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str|None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(10), default="info")   # info/warn/error
    status: Mapped[str] = mapped_column(String(20), default="new")      # new/read/acknowledged/closed
    target_scope: Mapped[str] = mapped_column(String(30), default="admin")  # owner/admin/manager/hr/finance/fleet_manager/person
    target_person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    due_at: Mapped[datetime|None] = mapped_column(DateTime)
    read_at: Mapped[datetime|None] = mapped_column(DateTime)
    acknowledged_at: Mapped[datetime|None] = mapped_column(DateTime)
    closed_at: Mapped[datetime|None] = mapped_column(DateTime)
    created_by: Mapped[str|None] = mapped_column(String(200))
    closed_by: Mapped[str|None] = mapped_column(String(200))

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(back_populates="notification")
    person: Mapped["Person|None"] = relationship(foreign_keys=[person_id])


class NotificationDelivery(Base):
    __tablename__ = "notification_delivery"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    notification_id: Mapped[str] = mapped_column(String(36), ForeignKey("notification.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")   # in_app/email/future_bot
    delivery_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/sent/failed/skipped
    recipient: Mapped[str|None] = mapped_column(String(200))
    delivery_attempted_at: Mapped[datetime|None] = mapped_column(DateTime)
    delivery_result: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    notification: Mapped["Notification"] = relationship(back_populates="deliveries")


class IntakeRecord(Base):
    __tablename__ = "intake_record"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    intake_type: Mapped[str] = mapped_column(String(30))   # odometer/claim/fine/fuel_note/general
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    vehicle_id: Mapped[str|None] = mapped_column(String(36))   # soft ref
    person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    source_channel: Mapped[str] = mapped_column(String(20), default="manual")  # manual/email/future_bot
    source_ref: Mapped[str|None] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str|None] = mapped_column(Text)
    payload_json: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new")   # new/reviewed/converted/ignored
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    reviewed_at: Mapped[datetime|None] = mapped_column(DateTime)
    reviewed_by: Mapped[str|None] = mapped_column(String(200))
    converted_type: Mapped[str|None] = mapped_column(String(30))
    converted_id: Mapped[str|None] = mapped_column(String(36))
    # Wave 3.3 — structured webhook intake fields
    source_provider: Mapped[str|None] = mapped_column(String(100))
    source_message_id: Mapped[str|None] = mapped_column(String(200))
    source_phone_e164: Mapped[str|None] = mapped_column(String(30))
    source_received_at: Mapped[str|None] = mapped_column(String(40))
    parsed_data: Mapped[str|None] = mapped_column(Text)
    attachments: Mapped[str|None] = mapped_column(Text)
    image_analysis: Mapped[str|None] = mapped_column(Text)
    confidence_score: Mapped[float|None] = mapped_column()
    unresolved_reason: Mapped[str|None] = mapped_column(Text)
    vehicle_resolution: Mapped[str|None] = mapped_column(String(20))
    audit_trail: Mapped[str|None] = mapped_column(Text)

    person: Mapped["Person|None"] = relationship(foreign_keys=[person_id])

from backend.core.models.kernel import Person, Entity
