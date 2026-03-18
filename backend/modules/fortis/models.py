"""
FORTIS — Economic data aggregator
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now


class FortisDocument(Base):
    __tablename__ = "fortis_document"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(30))
    source_system: Mapped[str] = mapped_column(String(30))
    source_ref: Mapped[str|None] = mapped_column(String(200))
    doc_number: Mapped[str|None] = mapped_column(String(100))
    doc_date: Mapped[str|None] = mapped_column(String(10))
    due_date: Mapped[str|None] = mapped_column(String(10))
    amount_gross: Mapped[float|None] = mapped_column(Float)
    amount_net: Mapped[float|None] = mapped_column(Float)
    amount_vat: Mapped[float|None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="CZK")
    counterparty_name: Mapped[str|None] = mapped_column(String(300))
    counterparty_ico: Mapped[str|None] = mapped_column(String(20))
    description: Mapped[str|None] = mapped_column(Text)
    cost_center: Mapped[str|None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="imported")
    paid_date: Mapped[str|None] = mapped_column(String(10))
    nexus_ref_type: Mapped[str|None] = mapped_column(String(50))
    nexus_ref_id: Mapped[str|None] = mapped_column(String(36))
    raw_data: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    entity: Mapped["Entity"] = relationship(foreign_keys=[entity_id])


class FortisCostRecord(Base):
    __tablename__ = "fortis_cost_record"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"), index=True)
    document_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("fortis_document.id"))
    cost_type: Mapped[str] = mapped_column(String(30))
    period_year: Mapped[int] = mapped_column(Integer, index=True)
    period_month: Mapped[int] = mapped_column(Integer, index=True)
    person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    vehicle_id: Mapped[str|None] = mapped_column(String(36))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="CZK")
    quantity: Mapped[float|None] = mapped_column(Float)
    unit: Mapped[str|None] = mapped_column(String(20))
    notes: Mapped[str|None] = mapped_column(Text)
    nexus_ref_type: Mapped[str|None] = mapped_column(String(50))
    nexus_ref_id: Mapped[str|None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    entity: Mapped["Entity"] = relationship(foreign_keys=[entity_id])
    document: Mapped["FortisDocument|None"] = relationship(foreign_keys=[document_id])


class FortisPayrollSummary(Base):
    __tablename__ = "fortis_payroll_summary"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"), index=True)
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    contract_type: Mapped[str|None] = mapped_column(String(20))
    gross_wage: Mapped[float|None] = mapped_column(Float)
    net_wage: Mapped[float|None] = mapped_column(Float)
    employer_total_cost: Mapped[float|None] = mapped_column(Float)
    social_ins_employee: Mapped[float|None] = mapped_column(Float)
    health_ins_employee: Mapped[float|None] = mapped_column(Float)
    income_tax: Mapped[float|None] = mapped_column(Float)
    deductions_fleet: Mapped[float|None] = mapped_column(Float)
    deductions_other: Mapped[float|None] = mapped_column(Float)
    meal_voucher_amount: Mapped[float|None] = mapped_column(Float)
    sport_benefit_amount: Mapped[float|None] = mapped_column(Float)
    document_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("fortis_document.id"))
    source: Mapped[str] = mapped_column(String(30), default="manual")
    notes: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    entity: Mapped["Entity"] = relationship(foreign_keys=[entity_id])


class FortisBankStatement(Base):
    __tablename__ = "fortis_bank_statement"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"), index=True)
    account_iban: Mapped[str|None] = mapped_column(String(50))
    transaction_date: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="CZK")
    direction: Mapped[str] = mapped_column(String(10))
    counterparty_name: Mapped[str|None] = mapped_column(String(300))
    counterparty_account: Mapped[str|None] = mapped_column(String(50))
    variable_symbol: Mapped[str|None] = mapped_column(String(20))
    constant_symbol: Mapped[str|None] = mapped_column(String(10))
    description: Mapped[str|None] = mapped_column(Text)
    matched_document_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("fortis_document.id"))
    match_status: Mapped[str] = mapped_column(String(20), default="unmatched")
    source_bank: Mapped[str|None] = mapped_column(String(50))
    raw_data: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    entity: Mapped["Entity"] = relationship(foreign_keys=[entity_id])


from backend.core.models.kernel import Entity, Person
