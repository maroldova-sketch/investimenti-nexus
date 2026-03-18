#!/usr/bin/env python3
"""
Seed script — loads fleet data from /config/nexus/fleet/
and creates demo users, entities, roles.
Run: python scripts/seed.py
"""
import sys, os, json
# Mac/local: path is set via PYTHONPATH=. or sys.path
import pathlib
ROOT = pathlib.Path(__file__).parent.parent.resolve()
os.chdir(ROOT)

from backend.core.models.base import engine, SessionLocal
from backend.core.models.kernel import (
    Base, Person, Entity, EntityType, UserAccount, RoleAssignment,
    NexusRole, ScopeType
)
from backend.modules.fleet.models import (
    Vehicle, VehicleAssignment, FuelCard, FuelTransactionStaging, FleetEvent
)
from backend.core.security.auth import hash_password
from backend.config import get_settings

settings = get_settings()

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables OK")

db = SessionLocal()

# ── ENTITIES ──────────────────────────────────────────────────────────────
entities_data = [
    {"code": "VZC",     "name": "Vaše Zubní Centrum",   "legal_name": "VAŠE ZUBNÍ CENTRUM s.r.o.", "entity_type": EntityType.COMPANY, "division": "health"},
    {"code": "LOGPACK", "name": "LOGPACK",               "legal_name": "LOGPACK s.r.o.",            "entity_type": EntityType.COMPANY, "division": "logistics"},
    {"code": "KERA",    "name": "KERA-DENS",             "legal_name": "KERA-DENS s.r.o.",          "entity_type": EntityType.CLINIC,  "division": "health"},
    {"code": "INV",     "name": "INVESTIMENTI",          "legal_name": "INVESTIMENTI s.r.o.",       "entity_type": EntityType.HOLDING, "division": None},
]
entity_map = {}
for ed in entities_data:
    e = db.query(Entity).filter(Entity.code == ed["code"]).first()
    if not e:
        e = Entity(**ed)
        db.add(e)
        db.flush()
    entity_map[ed["code"]] = e
db.commit()
print(f"Entities: {len(entity_map)}")

# ── ADMIN PERSON + USER ───────────────────────────────────────────────────
admin_person = db.query(Person).filter(Person.email_work == settings.nexus_admin_email).first()
if not admin_person:
    admin_person = Person(
        first_name="Admin",
        last_name="NEXUS",
        email_work=settings.nexus_admin_email,
        is_active=True,
    )
    db.add(admin_person)
    db.flush()

    admin_user = UserAccount(
        person_id=admin_person.id,
        email=settings.nexus_admin_email,
        hashed_password=hash_password(settings.nexus_admin_password),
        is_active=True,
    )
    db.add(admin_user)
    db.flush()

    role = RoleAssignment(
        person_id=admin_person.id,
        role=NexusRole.ADMIN,
        scope_type=ScopeType.ALL,
    )
    db.add(role)
    db.commit()
    print(f"Admin user: {settings.nexus_admin_email} / {settings.nexus_admin_password}")
else:
    print(f"Admin already exists: {settings.nexus_admin_email}")

# ── PEOPLE FROM DRIVERS.JSON ──────────────────────────────────────────────
fleet_data_dir = os.environ.get("NEXUS_DATA_DIR", str(ROOT.parent / "nexus-data")) + "/fleet"
with open(f"{fleet_data_dir}/drivers.json") as f:
    drivers_data = json.load(f)

person_map = {}  # external id → Person
for d in drivers_data["drivers"]:
    email = d.get("email_work") or d.get("email_personal")
    existing = None
    if email:
        existing = db.query(Person).filter(
            (Person.email_work == email) | (Person.email_personal == email)
        ).first()

    FUEL_MAP = {
        'N95':'N95','N100':'Natural100','Natural100':'Natural100',
        'Nafta':'Nafta','CNG':'CNG','N100+Nafta':'Natural100',
        'Benzin':'N95','?':None,
    }
    if not existing:
        p = Person(
            first_name=d["first"],
            last_name=d["last"],
            maiden_name=d.get("maiden"),
            email_work=d.get("email_work"),
            email_personal=d.get("email_personal"),
            phone=d.get("phone"),
            is_active=True,
        )
        db.add(p)
        db.flush()
        person_map[d["id"]] = p
    else:
        person_map[d["id"]] = existing
db.commit()
print(f"People loaded: {len(person_map)}")

# ── VEHICLES FROM VEHICLES.JSON ───────────────────────────────────────────
with open(f"{fleet_data_dir}/vehicles.json") as f:
    vehicles_data = json.load(f)

vehicle_map = {}
for vd in vehicles_data["vehicles"]:
    existing = None
    if vd.get("spz"):
        existing = db.query(Vehicle).filter(Vehicle.spz == vd["spz"]).first()
    if vd.get("vin") and not existing:
        existing = db.query(Vehicle).filter(Vehicle.vin == vd["vin"]).first()

    entity_code = vd.get("provoz")
    entity_id = entity_map.get(entity_code, {})
    entity_id = entity_id.id if hasattr(entity_id, 'id') else None


    FUEL_MAP = {
        'N95':'N95','N100':'Natural100','Natural100':'Natural100',
        'Nafta':'Nafta','CNG':'CNG','N100+Nafta':'Natural100',
        'Benzin':'N95','?':None,
    }
    if not existing:
        v = Vehicle(
            id=vd["id"],
            spz=vd.get("spz"),
            vin=vd.get("vin"),
            make=vd["make"],
            model=vd["model"],
            year=vd.get("year"),
            fuel_type=FUEL_MAP.get(vd.get('fuel',''), vd.get('fuel')),
            engine=vd.get("engine"),
            power_kw=vd.get("power_kw"),
            provoz=vd.get("provoz"),
            smlouva=vd.get("smlouva"),
            entity_id=entity_id,
            price_kc=vd.get("price_kc"),
            stk_valid_to=vd.get("stk"),
            insurance_contract_no=vd.get("pojistka"),
            phm_pref=vd.get("phm_pref"),
            status=vd.get("status", "aktivní"),
            notes=vd.get("note"),
        )
        db.add(v)
        db.flush()
        vehicle_map[vd["id"]] = v

        # Fuel cards
        axigon = vd.get("axigon")
        if axigon:
            cards = axigon.split("/") if "/" in str(axigon) else [str(axigon)]
            for c in cards:
                fc = FuelCard(vehicle_id=v.id, provider="Axigon", card_last4=c.strip()[-4:], is_active=True)
                db.add(fc)
    else:
        vehicle_map[vd["id"]] = existing

db.commit()
print(f"Vehicles loaded: {len(vehicle_map)}")

# ── DRIVER ASSIGNMENTS ────────────────────────────────────────────────────
with open(f"{fleet_data_dir}/driver_history.json") as f:
    history_data = json.load(f)

for h in history_data["assignments"]:
    vid = h["vehicle_id"]
    did = h["driver_id"]
    v = vehicle_map.get(vid)
    p = person_map.get(did)
    if not v or not p:
        continue
    existing = db.query(VehicleAssignment).filter(
        VehicleAssignment.vehicle_id == v.id,
        VehicleAssignment.person_id == p.id,
        VehicleAssignment.date_from == h["from"],
    ).first()

    FUEL_MAP = {
        'N95':'N95','N100':'Natural100','Natural100':'Natural100',
        'Nafta':'Nafta','CNG':'CNG','N100+Nafta':'Natural100',
        'Benzin':'N95','?':None,
    }
    if not existing:
        a = VehicleAssignment(
            vehicle_id=v.id,
            person_id=p.id,
            date_from=h["from"],
            date_to=h.get("to"),
            reason=h.get("reason"),
        )
        db.add(a)
db.commit()
print("Driver assignments loaded")

# ── PHM TRANSACTIONS ──────────────────────────────────────────────────────
with open(f"{fleet_data_dir}/phm_transactions.json") as f:
    phm_data = json.load(f)

for inv in phm_data.get("axigon_invoices", []):
    for item in inv.get("items", []):
        vid = item.get("vehicle_id") or item.get("vehicle_spz")
        v = vehicle_map.get(vid)
        if not v and item.get("vehicle_spz"):
            v = db.query(Vehicle).filter(Vehicle.spz == item["vehicle_spz"]).first()
        if not v:
            continue
        p = person_map.get(item.get("driver_id"))
        existing = db.query(FuelTransactionStaging).filter(
            FuelTransactionStaging.vehicle_id == v.id,
            FuelTransactionStaging.invoice_no == inv["invoice_no"],
            FuelTransactionStaging.fuel_type == item.get("fuel"),
        ).first()
    
    FUEL_MAP = {
        'N95':'N95','N100':'Natural100','Natural100':'Natural100',
        'Nafta':'Nafta','CNG':'CNG','N100+Nafta':'Natural100',
        'Benzin':'N95','?':None,
    }
    if not existing:
            t = FuelTransactionStaging(
                vehicle_id=v.id,
                person_id=p.id if p else None,
                period=inv["invoice_no"][:7].replace("326", "2026-03"),
                invoice_no=inv["invoice_no"],
                fuel_type=item.get("fuel"),
                litres=item.get("litres"),
                price_ex_vat=item.get("price_ex_vat"),
                price_inc_vat=item.get("price_inc_vat"),
                price_per_litre=item.get("ppl"),
                site=", ".join(item.get("sites", [])),
                source="axigon_pdf",
            )
            db.add(t)
db.commit()
print("PHM transactions loaded")

db.close()
print("\n✓ Seed complete")
print(f"  Login: {settings.nexus_admin_email}")
print(f"  Pass:  {settings.nexus_admin_password}")
print(f"  URL:   http://localhost:8000")

# Ensure new tables exist
from backend.modules.people.models import Employment
from backend.modules.attendance.models import (
    AttendancePeriod, AttendanceSubmission, LeaveRequest, ApprovalCase, PayrollExportBatch
)
Base.metadata.create_all(bind=engine)
print("New tables created (people/attendance/leave/approval/payroll)")
