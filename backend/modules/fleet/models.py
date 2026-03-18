"""
Fleet models — vehicles, assignments, fuel cards, PHM transactions, events.
Built on top of kernel, not replacing it.
"""
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now


class VehicleStatus(str, enum.Enum):
    ACTIVE = "aktivní"
    RESERVE = "rezervní"
    RETIRED = "vyřazeno"
    UNKNOWN = "neznámé"


class FuelType(str, enum.Enum):
    N95 = "N95"
    N100 = "Natural100"
    DIESEL = "Nafta"
    CNG = "CNG"
    ELECTRIC = "Elektro"
    HYBRID = "Hybrid"


class FleetEventType(str, enum.Enum):
    STK = "STK"
    SERVICE = "Servis"
    INCIDENT = "Pojistná událost"
    TYRE = "Výměna pneu"
    DRIVER_CHANGE = "Výměna řidiče"
    PURCHASE = "Nákup"
    BUYOUT = "Odkup"
    REPAIR = "Oprava"
    FINE = "Pokuta"
    RETIREMENT = "Vyřazení"
    OTHER = "Jiné"


# ─── VEHICLE ──────────────────────────────────────────────────────────────
class Vehicle(Base):
    __tablename__ = "vehicle"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    spz: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    vin: Mapped[str | None] = mapped_column(String(17), unique=True)
    make: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[int | None] = mapped_column(Integer)
    fuel_type: Mapped[str|None] = mapped_column(String(30))
    engine: Mapped[str | None] = mapped_column(String(60))
    power_kw: Mapped[int | None] = mapped_column(Integer)
    # Ownership / contract
    provoz: Mapped[str | None] = mapped_column(String(50))   # VZC / LOGPACK / KERA-DENS / Vlastní
    smlouva: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entity.id"))
    price_kc: Mapped[int | None] = mapped_column(Integer)
    lease_end: Mapped[str | None] = mapped_column(String(10))
    lease_contract_no: Mapped[str | None] = mapped_column(String(50))
    # Status & compliance
    status: Mapped[str] = mapped_column(SAEnum(VehicleStatus), default=VehicleStatus.ACTIVE)
    stk_valid_to: Mapped[str | None] = mapped_column(String(10))        # YYYY-MM-DD
    insurance_contract_no: Mapped[str | None] = mapped_column(String(50))
    highway_sticker_to: Mapped[str | None] = mapped_column(String(10))
    # PHM
    phm_pref: Mapped[str | None] = mapped_column(String(60))
    km_current: Mapped[int | None] = mapped_column(Integer)
    # Meta
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    assignments: Mapped[list["VehicleAssignment"]] = relationship(back_populates="vehicle")
    fuel_cards: Mapped[list["FuelCard"]] = relationship(back_populates="vehicle")
    events: Mapped[list["FleetEvent"]] = relationship(back_populates="vehicle")
    odometer_readings: Mapped[list["OdometerReading"]] = relationship(back_populates="vehicle")
    fuel_transactions: Mapped[list["FuelTransactionStaging"]] = relationship(back_populates="vehicle")

    @property
    def stk_status(self) -> str:
        if not self.stk_valid_to:
            return "unknown"
        from datetime import date
        today = date.today().isoformat()
        if self.stk_valid_to < today:
            return "expired"
        # warn if within 30 days
        from datetime import timedelta
        warn_date = (date.today() + timedelta(days=30)).isoformat()
        if self.stk_valid_to < warn_date:
            return "warn"
        return "ok"

    @property
    def display_name(self) -> str:
        return f"{self.make} {self.model}"

    @property
    def current_driver(self) -> "VehicleAssignment | None":
        for a in self.assignments:
            if a.date_to is None:
                return a
        return None


# ─── VEHICLE ASSIGNMENT ──────────────────────────────────────────────────
class VehicleAssignment(Base):
    __tablename__ = "vehicle_assignment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle.id"), index=True)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), index=True)
    date_from: Mapped[str] = mapped_column(String(10))
    date_to: Mapped[str | None] = mapped_column(String(10))
    reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="assignments")
    person: Mapped["Person"] = relationship()


# ─── FUEL CARD ───────────────────────────────────────────────────────────
class FuelCard(Base):
    __tablename__ = "fuel_card"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle.id"))
    provider: Mapped[str] = mapped_column(String(50))   # Axigon / innogy / Shell
    card_last4: Mapped[str | None] = mapped_column(String(10))
    card_number_masked: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(200))

    vehicle: Mapped["Vehicle | None"] = relationship(back_populates="fuel_cards")


# ─── FUEL TRANSACTION (STAGING) ──────────────────────────────────────────
class FuelTransactionStaging(Base):
    __tablename__ = "fuel_transaction_staging"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle.id"))
    person_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("person.id"))
    fuel_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("fuel_card.id"))
    period: Mapped[str | None] = mapped_column(String(7))    # 2026-03
    invoice_no: Mapped[str | None] = mapped_column(String(50))
    fuel_type: Mapped[str | None] = mapped_column(String(20))
    litres: Mapped[float | None] = mapped_column(Numeric(8, 2))
    price_ex_vat: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_inc_vat: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_per_litre: Mapped[float | None] = mapped_column(Numeric(6, 2))
    site: Mapped[str | None] = mapped_column(String(200))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    source: Mapped[str | None] = mapped_column(String(50))   # axigon_pdf / manual / api

    vehicle: Mapped["Vehicle | None"] = relationship(back_populates="fuel_transactions")
    person: Mapped["Person | None"] = relationship()


# ─── ODOMETER ────────────────────────────────────────────────────────────
class OdometerReading(Base):
    __tablename__ = "odometer_reading"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle.id"))
    km: Mapped[int] = mapped_column(Integer)
    reading_date: Mapped[str] = mapped_column(String(10))
    recorded_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("person.id"))
    notes: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="odometer_readings")


# ─── FLEET EVENT ─────────────────────────────────────────────────────────
class FleetEvent(Base):
    __tablename__ = "fleet_event"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle.id"), index=True)
    event_type: Mapped[str] = mapped_column(SAEnum(FleetEventType, native_enum=False, values_callable=lambda x: [e.value for e in x]))
    event_date: Mapped[str] = mapped_column(String(10))
    description: Mapped[str | None] = mapped_column(Text)
    cost_kc: Mapped[int | None] = mapped_column(Integer)
    created_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("person.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="events")


# ─── INSURANCE RECORD ────────────────────────────────────────────────────
class InsuranceRecord(Base):
    __tablename__ = "insurance_record"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle.id"))
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entity.id"))
    company: Mapped[str] = mapped_column(String(100))
    contract_no: Mapped[str | None] = mapped_column(String(60))
    insurance_type: Mapped[str | None] = mapped_column(String(60))
    valid_from: Mapped[str | None] = mapped_column(String(10))
    valid_to: Mapped[str | None] = mapped_column(String(10))
    contact_name: Mapped[str | None] = mapped_column(String(100))
    contact_email: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

# Fix import reference
from backend.core.models.kernel import Person


class FuelTransaction(Base):
    """Canonical fuel transaction — promoted from staging."""
    __tablename__ = "fuel_transaction"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle.id"), index=True)
    driver_person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    fuel_card_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("fuel_card.id"))
    transaction_date: Mapped[str|None] = mapped_column(String(10))   # YYYY-MM-DD
    month: Mapped[int|None] = mapped_column(Integer)
    year: Mapped[int|None] = mapped_column(Integer)
    amount_total: Mapped[float|None] = mapped_column(Numeric(10, 2))
    liters_total: Mapped[float|None] = mapped_column(Numeric(8, 3))
    vendor_name: Mapped[str|None] = mapped_column(String(100))
    source_doc_ref: Mapped[str|None] = mapped_column(String(100))
    source_staging_id: Mapped[str|None] = mapped_column(String(36))  # stg_fuel_monthly.id
    status: Mapped[str] = mapped_column(String(20), default="approved")
    reviewed_by: Mapped[str|None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vehicle: Mapped["Vehicle"] = relationship(foreign_keys=[vehicle_id])
    fuel_card: Mapped["FuelCard|None"] = relationship(foreign_keys=[fuel_card_id])


class InsuranceClaim(Base):
    __tablename__ = "insurance_claim"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle.id"), index=True)
    driver_person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    claim_date: Mapped[str|None] = mapped_column(String(10))
    location: Mapped[str|None] = mapped_column(String(200))
    description: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="open")   # open/investigating/closed/withdrawn
    insurer_ref: Mapped[str|None] = mapped_column(String(100))
    amount_claimed: Mapped[float|None] = mapped_column(Numeric(10, 2))
    amount_settled: Mapped[float|None] = mapped_column(Numeric(10, 2))
    photos_note: Mapped[str|None] = mapped_column(Text)
    created_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    vehicle: Mapped["Vehicle"] = relationship(foreign_keys=[vehicle_id])
    driver: Mapped["Person|None"] = relationship(foreign_keys=[driver_person_id])


class TrafficFine(Base):
    __tablename__ = "traffic_fine"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle.id"), index=True)
    driver_person_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    fine_date: Mapped[str|None] = mapped_column(String(10))
    amount: Mapped[float|None] = mapped_column(Numeric(10, 2))
    reason: Mapped[str|None] = mapped_column(String(300))
    due_date: Mapped[str|None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(30), default="open")   # open/paid/disputed/hr_deduction
    hr_deduction_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    payroll_period_target: Mapped[str|None] = mapped_column(String(20))
    created_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    vehicle: Mapped["Vehicle"] = relationship(foreign_keys=[vehicle_id])
    driver: Mapped["Person|None"] = relationship(foreign_keys=[driver_person_id])


class DeductionCase(Base):
    __tablename__ = "deduction_case"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), index=True)
    vehicle_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("vehicle.id"))
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    case_type: Mapped[str] = mapped_column(String(50))   # pokuta/škoda/spoluúčast/soukromé_phm/jiné
    amount: Mapped[float|None] = mapped_column(Numeric(10, 2))
    description: Mapped[str|None] = mapped_column(Text)
    legal_status: Mapped[str|None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft/pending_approval/approved/exported/closed
    payroll_period_target: Mapped[str|None] = mapped_column(String(20))
    source_ref_type: Mapped[str|None] = mapped_column(String(30))   # traffic_fine/insurance_claim/other
    source_ref_id: Mapped[str|None] = mapped_column(String(36))
    reviewed_by: Mapped[str|None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime|None] = mapped_column(DateTime)
    export_batch_id: Mapped[str|None] = mapped_column(String(36))
    exported_at: Mapped[datetime|None] = mapped_column(DateTime)
    exported_by: Mapped[str|None] = mapped_column(String(200))
    created_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    person: Mapped["Person"] = relationship(foreign_keys=[person_id])
    vehicle: Mapped["Vehicle|None"] = relationship(foreign_keys=[vehicle_id])


class TripLog(Base):
    __tablename__ = "trip_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle.id"), index=True)
    entity_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("entity.id"))
    trip_date: Mapped[str] = mapped_column(String(10))          # YYYY-MM-DD
    start_km: Mapped[int|None] = mapped_column(Integer)
    end_km: Mapped[int|None] = mapped_column(Integer)
    distance_km: Mapped[int|None] = mapped_column(Integer)      # persisted after validation
    trip_type: Mapped[str] = mapped_column(String(20), default="business")  # business/private/mixed
    purpose: Mapped[str|None] = mapped_column(String(300))
    destination: Mapped[str|None] = mapped_column(String(200))
    cost_center: Mapped[str|None] = mapped_column(String(100))
    notes: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/submitted/approved/ignored
    source: Mapped[str] = mapped_column(String(20), default="manual") # manual/imported/derived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_by: Mapped[str|None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime|None] = mapped_column(DateTime)
    created_by_id: Mapped[str|None] = mapped_column(String(36), ForeignKey("person.id"))

    person: Mapped["Person"] = relationship(foreign_keys=[person_id])
    vehicle: Mapped["Vehicle"] = relationship(foreign_keys=[vehicle_id])
