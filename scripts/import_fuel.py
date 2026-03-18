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
from backend.modules.staging.models import ImportBatch, ImportRowIssue, StgFuelMonthly
from backend.modules.staging.normalize import normalize_plate, normalize_company_hint
from backend.modules.staging.matcher import match_fuel_card

Base.metadata.create_all(engine)
db = SessionLocal()

raw = json.load(open(f"{FLEET_DIR}/phm_transactions.json", encoding="utf-8"))

def flatten_transactions(data):
    txs = []
    if isinstance(data, list):
        return data
    for key, val in data.items():
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    items = item.get("items") or item.get("transactions") or []
                    if items:
                        for tx in items:
                            tx.setdefault("invoice_no", item.get("invoice_no"))
                            tx.setdefault("entity", item.get("entity"))
                            tx.setdefault("period_from", item.get("period_from"))
                            txs.append(tx)
                    else:
                        txs.append(item)
    return txs

txs = flatten_transactions(raw)

batch = ImportBatch(source_type="fuel", source_filename="phm_transactions.json",
                    imported_by="import_fuel.py", status="parsed",
                    notes=f"{len(txs)} transactions flattened")
db.add(batch); db.flush()

ok = warn = 0
for i, tx in enumerate(txs):
    rr = f"row_{i+1}"
    spz = tx.get("spz") or tx.get("plate") or tx.get("vehicle_plate")
    plate = normalize_plate(spz)
    card = str(tx.get("card_last4") or tx.get("axigon_card") or tx.get("card") or "").strip() or None
    co = normalize_company_hint(tx.get("entity") or tx.get("company") or "")
    pf = tx.get("period_from") or ""
    try: year, month = int(pf[:4]), int(pf[5:7])
    except: year = month = None
    cid, ccid = match_fuel_card(db, card, plate)
    db.add(StgFuelMonthly(
        batch_id=batch.id, source_row_ref=rr,
        card_number_masked=card, plate_number=plate,
        driver_name_raw=tx.get("driver") or tx.get("ridic"),
        month=month, year=year,
        amount_total=tx.get("price_inc_vat") or tx.get("amount_czk") or tx.get("total_with_vat"),
        liters_total=tx.get("litres") or tx.get("liters"),
        source_doc_ref=tx.get("invoice_no"),
        company_hint=co, candidate_vehicle_id=cid, candidate_card_id=ccid,
        status="matched" if (cid or ccid) else "unresolved",
    ))
    if not plate and not card:
        db.add(ImportRowIssue(batch_id=batch.id, source_type="fuel", source_row_ref=rr,
            severity="warn", issue_code="NO_IDENTIFIER", issue_message="No plate or card",
            raw_snippet=json.dumps(tx, ensure_ascii=False)[:200]))
        warn += 1
    elif not cid and not ccid:
        db.add(ImportRowIssue(batch_id=batch.id, source_type="fuel", source_row_ref=rr,
            severity="info", issue_code="NO_VEHICLE_MATCH",
            issue_message=f"No match plate={plate} card={card}"))
        warn += 1
    else:
        ok += 1

batch.row_count = len(txs); batch.success_count = ok; batch.warning_count = warn; batch.status = "matched"
db.commit()
print(f"\n✓ Fuel import — DATA_DIR={DATA_DIR}")
print(f"  {len(txs)} rows | matched={ok} warn={warn}")
print(f"  Batch ID: {batch.id[:8]}")
db.close()
