from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now

class ImportBatch(Base):
    __tablename__ = "import_batch"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_type: Mapped[str] = mapped_column(String(30))
    source_filename: Mapped[str|None] = mapped_column(String(300))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    imported_by: Mapped[str|None] = mapped_column(String(200))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    notes: Mapped[str|None] = mapped_column(Text)
    issues: Mapped[list["ImportRowIssue"]] = relationship(back_populates="batch")

class ImportRowIssue(Base):
    __tablename__ = "import_row_issue"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batch.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_row_ref: Mapped[str|None] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(10), default="warn")
    issue_code: Mapped[str] = mapped_column(String(50))
    issue_message: Mapped[str] = mapped_column(Text)
    raw_snippet: Mapped[str|None] = mapped_column(Text)
    resolved_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_note: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    batch: Mapped["ImportBatch"] = relationship(back_populates="issues")

class StgPersonIntake(Base):
    __tablename__ = "stg_person_intake"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batch.id"), index=True)
    source_row_ref: Mapped[str|None] = mapped_column(String(50))
    full_name_raw: Mapped[str|None] = mapped_column(String(300))
    first_name: Mapped[str|None] = mapped_column(String(100))
    last_name: Mapped[str|None] = mapped_column(String(100))
    title_before: Mapped[str|None] = mapped_column(String(20))
    phone_raw: Mapped[str|None] = mapped_column(String(50))
    email_raw: Mapped[str|None] = mapped_column(String(200))
    address_raw: Mapped[str|None] = mapped_column(Text)
    personal_id_raw_masked: Mapped[str|None] = mapped_column(String(30))
    bank_account_raw_masked: Mapped[str|None] = mapped_column(String(50))
    insurance_raw: Mapped[str|None] = mapped_column(String(100))
    company_hint: Mapped[str|None] = mapped_column(String(50))
    location_hint: Mapped[str|None] = mapped_column(String(100))
    role_hint: Mapped[str|None] = mapped_column(String(100))
    normalized_name: Mapped[str|None] = mapped_column(String(200))
    normalized_email: Mapped[str|None] = mapped_column(String(200))
    normalized_phone: Mapped[str|None] = mapped_column(String(30))
    candidate_person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    match_confidence: Mapped[str|None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class StgVehicleRegistry(Base):
    __tablename__ = "stg_vehicle_registry"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batch.id"), index=True)
    source_row_ref: Mapped[str|None] = mapped_column(String(50))
    vehicle_name_raw: Mapped[str|None] = mapped_column(String(200))
    plate_number: Mapped[str|None] = mapped_column(String(20))
    vin: Mapped[str|None] = mapped_column(String(50))
    driver_name_raw: Mapped[str|None] = mapped_column(String(200))
    company_hint: Mapped[str|None] = mapped_column(String(50))
    cost_center_hint: Mapped[str|None] = mapped_column(String(50))
    insurance_expiry: Mapped[str|None] = mapped_column(String(20))
    stk_expiry: Mapped[str|None] = mapped_column(String(20))
    lease_end: Mapped[str|None] = mapped_column(String(20))
    notes_raw: Mapped[str|None] = mapped_column(Text)
    candidate_vehicle_id: Mapped[str|None] = mapped_column(String(36))
    candidate_person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class StgPayrollMonthly(Base):
    __tablename__ = "stg_payroll_monthly"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batch.id"), index=True)
    source_row_ref: Mapped[str|None] = mapped_column(String(50))
    company_code: Mapped[str|None] = mapped_column(String(20))
    location_code: Mapped[str|None] = mapped_column(String(50))
    employee_name_raw: Mapped[str|None] = mapped_column(String(200))
    normalized_name: Mapped[str|None] = mapped_column(String(200))
    month: Mapped[int|None] = mapped_column(Integer)
    year: Mapped[int|None] = mapped_column(Integer)
    attendance_days: Mapped[float|None] = mapped_column(Float)
    leave_days: Mapped[float|None] = mapped_column(Float)
    salary_component_raw: Mapped[str|None] = mapped_column(Text)
    position_hint: Mapped[str|None] = mapped_column(String(100))
    contract_hint: Mapped[str|None] = mapped_column(String(50))
    candidate_person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    candidate_employment_id: Mapped[str|None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class StgFuelMonthly(Base):
    __tablename__ = "stg_fuel_monthly"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batch.id"), index=True)
    source_row_ref: Mapped[str|None] = mapped_column(String(50))
    card_number_masked: Mapped[str|None] = mapped_column(String(20))
    plate_number: Mapped[str|None] = mapped_column(String(20))
    driver_name_raw: Mapped[str|None] = mapped_column(String(200))
    month: Mapped[int|None] = mapped_column(Integer)
    year: Mapped[int|None] = mapped_column(Integer)
    amount_total: Mapped[float|None] = mapped_column(Float)
    liters_total: Mapped[float|None] = mapped_column(Float)
    source_doc_ref: Mapped[str|None] = mapped_column(String(100))
    company_hint: Mapped[str|None] = mapped_column(String(50))
    candidate_vehicle_id: Mapped[str|None] = mapped_column(String(36))
    candidate_card_id: Mapped[str|None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

from backend.core.models.kernel import Person
