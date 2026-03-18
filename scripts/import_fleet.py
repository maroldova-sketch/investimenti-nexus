#!/usr/bin/env python3
import os, json, pathlib, sys

ROOT = pathlib.Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

# Load .env
env_file = ROOT / '.env'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

DATA_DIR = os.environ.get('NEXUS_DATA_DIR', str(ROOT.parent / 'nexus-data'))
FLEET_DIR = DATA_DIR + '/fleet'

from backend.core.models.base import SessionLocal, Base, engine
from backend.modules.staging.models import ImportBatch, ImportRowIssue, StgVehicleRegistry, StgPersonIntake
from backend.modules.staging.normalize import normalize_plate, normalize_company_hint, normalize_name, normalize_email, normalize_phone, split_name
from backend.modules.staging.matcher import match_vehicle, match_person

Base.metadata.create_all(engine)
db = SessionLocal()

# VEHICLES
raw = json.load(open(f"{FLEET_DIR}/vehicles.json", encoding="utf-8"))
vehicles = raw.get("vehicles", raw) if isinstance(raw, dict) else raw

vb = ImportBatch(source_type="fleet", source_filename="vehicles.json",
                 imported_by="import_fleet.py", status="parsed")
db.add(vb); db.flush()
v_ok = v_warn = 0
for i, vd in enumerate(vehicles):
    rr = f"row_{i+1}"
    plate = normalize_plate(vd.get("spz"))
    vin = vd.get("vin") or None
    co = normalize_company_hint(vd.get("provoz") or vd.get("entity") or "")
    drv = vd.get("driver") or vd.get("ridic") or None
    cand_vid = match_vehicle(db, vin, plate)
    cand_pid, _ = match_person(db, None, None, normalize_name(drv), co) if drv else (None, None)
    db.add(StgVehicleRegistry(
        batch_id=vb.id, source_row_ref=rr,
        vehicle_name_raw=f"{vd.get('make','')} {vd.get('model','')}".strip() or None,
        plate_number=plate, vin=vin, driver_name_raw=drv, company_hint=co,
        stk_expiry=vd.get("stk_valid_to") or vd.get("stk"),
        notes_raw=vd.get("notes"),
        candidate_vehicle_id=cand_vid, candidate_person_id=cand_pid,
        status="matched" if cand_vid else "unresolved",
    ))
    if not plate:
        db.add(ImportRowIssue(batch_id=vb.id, source_type="fleet", source_row_ref=rr,
            severity="warn", issue_code="MISSING_PLATE", issue_message="No plate"))
        v_warn += 1
    elif not cand_vid:
        db.add(ImportRowIssue(batch_id=vb.id, source_type="fleet", source_row_ref=rr,
            severity="info", issue_code="NO_VEHICLE_MATCH",
            issue_message=f"No canonical vehicle for plate={plate} vin={vin}"))
        v_warn += 1
    else:
        v_ok += 1
vb.row_count = len(vehicles); vb.success_count = v_ok; vb.warning_count = v_warn; vb.status = "matched"

# DRIVERS
raw2 = json.load(open(f"{FLEET_DIR}/drivers.json", encoding="utf-8"))
drivers = raw2.get("drivers", raw2) if isinstance(raw2, dict) else raw2

pb = ImportBatch(source_type="people", source_filename="drivers.json",
                 imported_by="import_fleet.py", status="parsed")
db.add(pb); db.flush()
p_ok = p_warn = p_err = 0
for i, d in enumerate(drivers):
    rr = f"row_{i+1}"
    full = d.get("full") or d.get("name") or f"{d.get('first','')} {d.get('last','')}".strip()
    title, first, last = split_name(full)
    first = first or d.get("first"); last = last or d.get("last")
    email = normalize_email(d.get("email_work") or d.get("email"))
    phone = normalize_phone(d.get("phone"))
    ents = d.get("entity", [])
    co = normalize_company_hint(ents[0] if isinstance(ents, list) and ents else (ents or ""))
    nm = normalize_name(full)
    cand_pid, conf = match_person(db, email, phone, nm, co)
    db.add(StgPersonIntake(
        batch_id=pb.id, source_row_ref=rr,
        full_name_raw=full, first_name=first, last_name=last, title_before=title,
        phone_raw=d.get("phone"), email_raw=email,
        company_hint=co, role_hint=d.get("role"),
        normalized_name=nm, normalized_email=email, normalized_phone=phone,
        candidate_person_id=cand_pid, match_confidence=conf,
        status="matched" if cand_pid else "unresolved",
    ))
    if not full.strip():
        p_err += 1
        db.add(ImportRowIssue(batch_id=pb.id, source_type="people", source_row_ref=rr,
            severity="error", issue_code="MISSING_NAME", issue_message="No name"))
    elif not cand_pid:
        p_warn += 1
        db.add(ImportRowIssue(batch_id=pb.id, source_type="people", source_row_ref=rr,
            severity="info", issue_code="NO_PERSON_MATCH",
            issue_message=f"No match for '{full}'"))
    else:
        p_ok += 1
pb.row_count = len(drivers); pb.success_count = p_ok; pb.warning_count = p_warn
pb.error_count = p_err; pb.status = "matched"

db.commit()
print(f"\n✓ Fleet import complete — DATA_DIR={DATA_DIR}")
print(f"  Vehicles: {len(vehicles)} rows | matched={v_ok} warn={v_warn}")
print(f"  Drivers:  {len(drivers)} rows | matched={p_ok} warn={p_warn} err={p_err}")
print(f"  Batch IDs: vehicles={vb.id[:8]} people={pb.id[:8]}")
db.close()
