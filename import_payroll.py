import pandas as pd, uuid, re
from datetime import datetime
from sqlalchemy import text
import sys
sys.path.insert(0, '/Users/investimenti/Projects/nexus')
from backend.core.models.base import SessionLocal

db = SessionLocal()
now = datetime.now()

entities = {r[0]: r[1] for r in db.execute(text('SELECT code, id FROM entity')).fetchall()}

# Person lookup by name
persons_raw = db.execute(text("SELECT id, first_name || ' ' || last_name full_name FROM person WHERE is_active=1")).fetchall()
person_map = {r[1].strip(): r[0] for r in persons_raw}

def find_person(name):
    name = str(name).strip()
    if name in person_map: return person_map[name]
    # Try reversed
    parts = name.split()
    if len(parts) == 2:
        rev = parts[1] + ' ' + parts[0]
        if rev in person_map: return person_map[rev]
    # Partial
    for k, v in person_map.items():
        if name.lower() in k.lower() or k.lower() in name.lower():
            return v
    return None

def safe_float(v):
    try:
        f = float(str(v).replace(' ','').replace(',','.'))
        return f if f > 0 else None
    except: return None

def load_sheet(path, sheet, entity_id, yr, mo):
    df = pd.read_excel(path, sheet_name=sheet, header=None, engine='openpyxl')
    # Find header
    hdr = None
    for i, row in df.iterrows():
        if any('Jméno' in str(v) or 'jmeno' in str(v).lower() for v in row):
            hdr = i; break
    if hdr is None: return 0
    
    df2 = pd.read_excel(path, sheet_name=sheet, header=hdr, engine='openpyxl')
    inserted = 0
    
    for _, row in df2.iterrows():
        name = str(row.get('Jméno', '') or '').strip()
        if not name or name == 'nan' or name.startswith('Celkem') or name.startswith('CELKEM'):
            continue
        
        zaklad = safe_float(row.get('Základ'))
        dpp = safe_float(row.get('DPP'))
        osobni = safe_float(row.get('Os.ohod.'))
        kafeterie = safe_float(row.get('Kafeterie'))
        multisport = safe_float(row.get('Multisport'))
        obed = safe_float(row.get('Obědy'))
        parkovne = safe_float(row.get('Parkovné'))
        srazka = safe_float(row.get('Srážka'))
        
        # Gross = zaklad + osobni (HPP part)
        gross = (zaklad or 0) + (osobni or 0)
        # If no zaklad but has DPP only = DPP contract
        contract = 'HPP' if zaklad else ('DPP' if dpp else 'unknown')
        if dpp and not zaklad:
            gross = dpp
        
        benefits = (kafeterie or 0) + (multisport or 0) + (obed or 0) + (parkovne or 0)
        
        # Employer cost estimate: gross * 1.338 (34% odvody)
        employer_cost = round(gross * 1.338, 0) if gross else None
        
        person_id = find_person(name)
        
        # Skip if already exists
        ex = db.execute(text('''SELECT id FROM fortis_payroll_summary 
            WHERE entity_id=:eid AND period_year=:yr AND period_month=:mo 
            AND (person_id=:pid OR (person_id IS NULL AND notes LIKE :name_like))'''),
            {'eid': entity_id, 'yr': yr, 'mo': mo, 'pid': person_id or '', 'name_like': f'%{name}%'}).fetchone()
        if ex: continue
        
        db.execute(text('''INSERT INTO fortis_payroll_summary
            (id, entity_id, period_year, period_month, person_id, contract_type,
             gross_wage, employer_total_cost, meal_voucher_amount, sport_benefit_amount,
             deductions_fleet, source, notes, created_at)
            VALUES (:id,:eid,:yr,:mo,:pid,:ct,:gross,:emp_cost,:meal,:sport,:ded,'xlsx_import',:notes,:now)
        '''), {
            'id': str(uuid.uuid4()), 'eid': entity_id, 'yr': yr, 'mo': mo,
            'pid': person_id, 'ct': contract,
            'gross': gross if gross > 0 else None,
            'emp_cost': employer_cost,
            'meal': (obed or 0) + (kafeterie or 0) if (obed or kafeterie) else None,
            'sport': multisport,
            'ded': srazka,
            'notes': f'{name} | {str(row.get("Pozice",""))}',
            'now': now
        })
        inserted += 1
    
    return inserted

# Map: (file, sheet, entity_code, year, month)
imports = [
    ('data/mzdy/2026_01_MZDY_KOMPLET_FINAL_VZC.xlsx', 'VZC_01_2026', 'VZC', 2026, 1),
    ('data/mzdy/2026_01_MZDY_KOMPLET_FINAL_VZC.xlsx', 'LOUNY_01_2026', 'VZC-LN', 2026, 1),
    ('data/mzdy/2026_01_MZDY_KOMPLET_FINAL_VZC.xlsx', 'ÚSTÍ_01_2026', 'VZC-UL', 2026, 1),
    ('data/mzdy/2026_01_MZDY_KOMPLET_FINAL_KERA.xlsx', 'KERA_01_2026', 'KERA', 2026, 1),
    ('data/mzdy/2026_02_MZDY_KOMPLET_DOPLNENO_MATKA_VZC_dcery.xlsx', 'VZC_02_2026', 'VZC', 2026, 2),
    ('data/mzdy/2026_02_MZDY_KOMPLET_DOPLNENO_MATKA_VZC_dcery.xlsx', 'LOUNY_02_2026', 'VZC-LN', 2026, 2),
    ('data/mzdy/2026_02_MZDY_KOMPLET_DOPLNENO_MATKA_VZC_dcery.xlsx', 'ÚSTÍ_02_2026', 'VZC-UL', 2026, 2),
    ('data/mzdy/2026_02_MZDY_KOMPLET_DOPLNENO_KERA.xlsx', 'KERA_02_2026', 'KERA', 2026, 2),
]

total = 0
for path, sheet, ent_code, yr, mo in imports:
    eid = entities.get(ent_code)
    if not eid:
        print(f'  Entity not found: {ent_code}'); continue
    try:
        n = load_sheet(path, sheet, eid, yr, mo)
        print(f'{ent_code} {yr}/{mo:02d} [{sheet}]: +{n}')
        total += n
    except Exception as e:
        print(f'  ERROR {ent_code} {sheet}: {e}')

db.commit()
print(f'\nCelkem vloženo: {total}')

# Summary per entity/month
print('\n=== FORTIS Payroll Summary ===')
rows = db.execute(text('''
    SELECT e.code, fps.period_year, fps.period_month,
           COUNT(*) cnt,
           SUM(CASE WHEN fps.contract_type IN ("HPP","JEDNATEL") THEN 1 ELSE 0 END) hpp,
           SUM(CASE WHEN fps.contract_type="DPP" THEN 1 ELSE 0 END) dpp_cnt,
           ROUND(SUM(fps.gross_wage),0) gross,
           ROUND(SUM(fps.employer_total_cost),0) emp_cost
    FROM fortis_payroll_summary fps
    JOIN entity e ON e.id=fps.entity_id
    GROUP BY e.code, fps.period_year, fps.period_month
    ORDER BY fps.period_year, fps.period_month, e.code
''')).fetchall()

for r in rows:
    gross = float(r[6] or 0); emp = float(r[7] or 0)
    print(f'  {r[0]:8} {r[1]}/{r[2]:02d} | {r[3]:3} osob ({r[4]} HPP + {r[5]} DPP) | hrubá mzda: {gross:>10,.0f} Kč | náklad: {emp:>10,.0f} Kč')

total_rec = db.execute(text('SELECT COUNT(*) FROM fortis_payroll_summary')).scalar()
print(f'\nCelkem záznamů: {total_rec}')
db.close()
