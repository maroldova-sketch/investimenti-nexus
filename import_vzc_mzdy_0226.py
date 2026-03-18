
import os, re, subprocess, zipfile, sys, uuid
from datetime import datetime
sys.path.insert(0, '/Users/investimenti/Projects/nexus')
from sqlalchemy import text
from backend.core.models.base import SessionLocal

ZIP = '/Users/investimenti/Projects/nexus/data/mzdy/VZC_MZDY_2026-02.zip'
YEAR, MONTH = 2026, 2
FILE_MAP = {
    'VZC Seznam mezd 2.2026.pdf': 'VZC',
    'VZC Louny Seznam mezd 2.2026.pdf': 'VZC-LN',
    'VZC \xdast\xed Seznam mezd 2.2026.pdf': 'VZC-UL',
}

db = SessionLocal()
entity_ids = {}
for code in ['VZC','VZC-LN','VZC-UL']:
    r = db.execute(text('SELECT id FROM entity WHERE code=:c'), {'c': code}).fetchone()
    entity_ids[code] = r[0] if r else None

persons = {}
for pid,ln,fn in db.execute(text('SELECT id,last_name,first_name FROM person WHERE is_active=1')).fetchall():
    persons['{} {}'.format(ln,fn).lower()] = pid
    if ln.lower() not in persons:
        persons[ln.lower()] = pid
print('Persons loaded:', len(persons))

def parse_pdf(pdf_bytes):
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
        tf.write(pdf_bytes); tfn = tf.name
    out = subprocess.run(['/opt/homebrew/bin/pdftotext','-layout',tfn,'-'], capture_output=True, text=True, timeout=20).stdout
    os.unlink(tfn)
    records = []
    for line in out.split('\n'):
        # Lines: "2.2026   Name Name (code)   18,000   144,00   0   3176  0  34676  ..."
        m = re.match(r'^2\.2026\s+(.+?)\s{2,}((?:[\d,]+\s+){5,})', line)
        if not m:
            continue
        name_raw = m.group(1).strip()
        nums_str = m.group(2)
        nums = re.findall(r'[\d]+(?:,\d+)?', nums_str)
        if len(nums) < 6:
            continue
        def n(i):
            try: return float(nums[i].replace(',','.'))
            except: return 0.0
        hruba = n(5)
        if hruba == 0:
            continue
        name_clean = re.sub(r'\s*\([^)]+\)\s*$', '', name_raw).strip()
        parts = name_clean.split()
        last = parts[0] if parts else name_clean
        first = ' '.join(parts[1:]) if len(parts) > 1 else ''
        pid = persons.get('{} {}'.format(last,first).lower()) or persons.get(last.lower())
        records.append({
            'name': name_raw[:100], 'person_id': pid,
            'gross': hruba, 'net': n(12),
            'hi': n(6), 'si': n(7), 'tax': n(11), 'ded': n(14),
        })
    return records

zf = zipfile.ZipFile(ZIP)
total_ok = total_dup = total_unm = 0

for fname, code in FILE_MAP.items():
    eid = entity_ids.get(code)
    if not eid:
        print('SKIP', code)
        continue
    try:
        pdf_data = zf.read(fname)
    except Exception as e:
        print('ERROR reading', fname, e)
        continue
    recs = parse_pdf(pdf_data)
    ok = dup = unm = 0
    for rec in recs:
        ex = db.execute(text('SELECT id FROM fortis_payroll_summary WHERE entity_id=:e AND period_year=:y AND period_month=:m AND notes=:n'),
                       {'e':eid,'y':YEAR,'m':MONTH,'n':rec['name']}).fetchone()
        if ex:
            dup += 1
            continue
        if not rec['person_id']:
            unm += 1
            print('  UNMATCHED:', rec['name'])
        db.execute(text('INSERT INTO fortis_payroll_summary (id,entity_id,person_id,period_year,period_month,gross_wage,net_wage,health_ins_employee,social_ins_employee,income_tax,deductions_other,source,notes,created_at) VALUES (:id,:e,:p,:y,:m,:gw,:nw,:hi,:si,:it,:ded,:src,:nm,:now)'),
            {'id':str(uuid.uuid4()),'e':eid,'p':rec['person_id'],'y':YEAR,'m':MONTH,'gw':rec['gross'],'nw':rec['net'],'hi':rec['hi'],'si':rec['si'],'it':rec['tax'],'ded':rec['ded'],'src':'pdf_vzc_0226','nm':rec['name'],'now':datetime.utcnow()})
        ok += 1
    db.commit()
    print('{}: {} parsed | {} inserted | {} dupes | {} unmatched'.format(code, len(recs), ok, dup, unm))
    total_ok += ok; total_dup += dup; total_unm += unm

print('TOTAL: {} inserted | {} dupes | {} unmatched'.format(total_ok, total_dup, total_unm))
db.close()
