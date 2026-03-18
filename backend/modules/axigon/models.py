"""Wave 3.2 — Axigon account, contacts, intake sources. Plain String statuses."""
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Numeric, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now


class ExternalAccount(Base):
    __tablename__ = "external_account"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"), index=True)
    provider_code: Mapped[str] = mapped_column(String(30))          # axigon / other
    status: Mapped[str] = mapped_column(String(20), default="active")
    login_name: Mapped[str|None] = mapped_column(String(200))
    contact_email: Mapped[str|None] = mapped_column(String(200))
    registration_type: Mapped[str|None] = mapped_column(String(100))  # Premium / Standard
    registration_valid_to: Mapped[str|None] = mapped_column(String(10))  # YYYY-MM-DD
    deposit_amount: Mapped[float|None] = mapped_column(Numeric(12, 2))
    registered_address: Mapped[str|None] = mapped_column(String(300))
    delivery_address: Mapped[str|None] = mapped_column(String(300))
    notes: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    contacts: Mapped[list["ExternalContact"]] = relationship(back_populates="account")
    entity: Mapped["Entity|None"] = relationship(foreign_keys=[entity_id])


class ExternalContact(Base):
    __tablename__ = "external_contact"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    external_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_account.id"), index=True)
    contact_type: Mapped[str] = mapped_column(String(20), default="person")  # person / department
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str|None] = mapped_column(String(200))
    phone: Mapped[str|None] = mapped_column(String(50))
    login_name: Mapped[str|None] = mapped_column(String(200))
    mobile_app_access: Mapped[bool] = mapped_column(Boolean, default=False)
    send_invoices: Mapped[bool] = mapped_column(Boolean, default=False)
    send_price_lists: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    account: Mapped["ExternalAccount"] = relationship(back_populates="contacts")
    assignments: Mapped[list["ExternalContactAssignment"]] = relationship(back_populates="contact")


class ExternalContactAssignment(Base):
    __tablename__ = "external_contact_assignment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    external_contact_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_contact.id"), index=True)
    area: Mapped[str] = mapped_column(String(30))          # contracts / fuel_cards / billing
    priority: Mapped[str] = mapped_column(String(20), default="primary")   # primary / secondary
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    contact: Mapped["ExternalContact"] = relationship(back_populates="assignments")


class IntakeSource(Base):
    __tablename__ = "intake_source"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(60), unique=True)  # mailbox_faktury_logpack / wflow
    source_type: Mapped[str] = mapped_column(String(20))        # mailbox / workflow / manual
    display_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active")
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    default_for_type: Mapped[str|None] = mapped_column(String(40))  # fuel_invoice / phm / billing
    notes: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    entity: Mapped["Entity|None"] = relationship(foreign_keys=[entity_id])

from backend.core.models.kernel import Entity
