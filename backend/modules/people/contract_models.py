"""
Wave 3.4 — Employment contracts & tariffs
One person can have multiple contracts (HPP + DPP simultaneously across entities).
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.models.base import Base
from backend.core.models.kernel import _uuid, _now


class EmploymentContract(Base):
    """
    Smluvní vztah osoby k entitě.
    Typy: HPP, DPP, DPC, OSVČ/faktura, statutár, jednatel, dobrovolník.
    Jedna osoba může mít více aktivních smluv (různé entity, různé typy).
    """
    __tablename__ = "employment_contract"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("person.id"), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entity.id"), index=True)

    # Typ smluvního vztahu
    contract_type: Mapped[str] = mapped_column(String(30))
    # HPP = hlavní pracovní poměr
    # DPP = dohoda o provedení práce
    # DPC = dohoda o pracovní činnosti
    # OSVČ = fakturující OSVČ
    # JEDNATEL = jednatel / statutár
    # DOBROVOLNIK = bez nároku na odměnu

    # Název pozice v rámci této smlouvy
    position_title: Mapped[str | None] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(200))
    work_location: Mapped[str | None] = mapped_column(String(100))

    # Tarif / odměna
    salary_type: Mapped[str] = mapped_column(String(20), default="monthly")
    # monthly = měsíční paušál, hourly = hodinová sazba, commission = provize, fixed = fixní odměna/smlouva
    salary_amount: Mapped[float | None] = mapped_column(Float)        # Kč
    hourly_rate: Mapped[float | None] = mapped_column(Float)          # Kč/hod (pokud hourly)
    currency: Mapped[str] = mapped_column(String(3), default="CZK")

    # Pracovní úvazek
    weekly_hours: Mapped[float | None] = mapped_column(Float)         # 40 = plný, 20 = poloviční
    is_full_time: Mapped[bool] = mapped_column(Boolean, default=True)

    # Platnost
    valid_from: Mapped[str | None] = mapped_column(String(10))        # YYYY-MM-DD
    valid_to: Mapped[str | None] = mapped_column(String(10))          # null = otevřený konec
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Číslo smlouvy, interní ref
    contract_number: Mapped[str | None] = mapped_column(String(100))
    internal_ref: Mapped[str | None] = mapped_column(String(100))

    # Benefity a srážky
    meal_voucher: Mapped[bool] = mapped_column(Boolean, default=False) # stravenky/gastro
    meal_voucher_amount: Mapped[float | None] = mapped_column(Float)
    transport_allowance: Mapped[float | None] = mapped_column(Float)   # příspěvek na dopravu
    notes: Mapped[str | None] = mapped_column(Text)

    # Metadata
    created_by: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    person: Mapped["Person"] = relationship(foreign_keys=[person_id])
    entity: Mapped["Entity"] = relationship(foreign_keys=[entity_id])

    @property
    def is_current(self) -> bool:
        from datetime import date
        today = date.today().isoformat()
        if self.valid_to and self.valid_to < today:
            return False
        return self.is_active


from backend.core.models.kernel import Person, Entity
