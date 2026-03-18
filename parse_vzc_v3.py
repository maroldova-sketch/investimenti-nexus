import subprocess, re, uuid, os, glob
from datetime import datetime
from sqlalchemy import text
import sys
sys.path.insert(0, '/Users/investimenti/Projects/nexus')
from backend.core.models.base import SessionLocal

db = SessionLocal()
now = datetime.now()
entities = {r[0]: r[1] for r in db.execute(text('SELECT code, id FROM entity')).fetchall()}
VZC = entities['VZC']

veh = {r[0]: (r[1], r[2]) for r in db.execute(text('SELECT spz, id, entity_id FROM vehicle WHERE spz IS NOT NULL')).fetchall()}

def resolve_card(label):
    label = str(label).strip()
    m = re.search(r'\b([0-9][A-Z0-9]{6,8})\b', label)
    if m: return m.group(1)
    clean = re.sub(r'\s+', '', label.upper())
    for key, spz in [
        ('SERGEYEV', '1UT4267'), ('VOZNIAK', '1UN7000'),
        ('LABORAT', '9U59758'), ('CITIGO', '9U59758'),
        ('1UN7393', '1UN7393'), ('1UN7000', '1UN7000'),
        ('6SF6085', '6SF6085'), ('6AJ3128', '6AJ3128'),
        ('6Z78554', '6Z78554'), ('9U42597', '9U42597'),
        ('9U35678', '9U35678'), ('9U75702', '9U75702'),
    ]:
        if key in clean: return spz
    return None

def parse_num(s):
    s = str(s).strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
    try: return float(s)
    except: return None

def parse_pdf(pdf_path):
    result = subprocess.run(
        ['/opt/homebrew/bin/pdftotext', '-layout', pdf_path, '-'],
        capture_output=True, text=True, timeout=15
    )
    text = result.stdout
    fname = os.path.basename(pdf_path)
    inv_no = fname.replace('faktura.pdf', '').replace('.pdf', '')

    # Period from text
    pm = re.search(r'Fakturované období:\s*[\d\.]+\s*[-–]\s*(\d+)\.(\d+)\.(\d{4})', text)
    if pm:
        yr, mo = int(pm.group(3)), int(pm.group(2))
    else:
        dm = re.search(r'Datum vystavení:\s*(\d{2})\.(\d{2})\.(\d{4})', text)
        yr = int(dm.group(3)) if dm else 2025
        mo = int(dm.group(2)) if dm else 6

    transactions = []
    current_card = None

    for line in text.split('\n'):
        # Card header: "Číslo karty: XXXX    ID karty: Superb 6SF6085"
        cm = re.search(r'ID karty:\s*(.+?)(?:\s{3,}|$)', line)
        if cm and 'ID karty:' in line:
            current_card = cm.group(1).strip()
            continue

        # Transaction line: starts with "CZ " + date
        # CZ  28.12.25  12:01  346408  Shell CZ  8107 Shell ...  Nafta  51,12  ...  2131,87
        m = re.match(r'^CZ\s+(\d{2}\.\d{2}\.\d{2,4})\s+(\d{2}:\d{2})\s+(\S+)\s+(.+?)\s{2,}(.+?)\s{2,}(\S+)\s+.*?([\d ]+[,\.]\d{2})\s*$', line)
        if m and current_card:
            date_str, time_str, receipt, network, place_fuel, fuel2, total_str = m.groups()
            # date
            dm2 = re.match(r'(\d{2})\.(\d{2})\.(\d{2,4})', date_str)
            if dm2:
                d, m2, y = int(dm2.group(1)), int(dm2.group(2)), int(dm2.group(3))
                if y < 100: y += 2000
                td = f'{y}-{m2:02d}-{d:02d}'
                txn_yr, txn_mo = y, m2
            else:
                td = f'{yr}-{mo:02d}-01'; txn_yr, txn_mo = yr, mo

            total = parse_num(total_str)
            # Extract qty and fuel name from the combined columns
            # Full line split by 2+ spaces gives better columns
            cols = re.split(r'\s{2,}', line.strip())
            # cols: [CZ, date, time, receipt, network, place, fuel, qty, price1, price2, vat%, netto, dph, total]
            qty = None
            fuel_name = ''
            if len(cols) >= 8:
                fuel_name = cols[6] if len(cols) > 6 else ''
                qty = parse_num(cols[7]) if len(cols) > 7 else None

            ref = f'{inv_no}_{receipt}_{td}'
            transactions.append({
                'card': current_card,
                'date': td, 'yr': txn_yr, 'mo': txn_mo,
                'station': cols[5] if len(cols) > 5 else '',
                'fuel': fuel_name,
                'qty': qty,
                'total': total,
                'ref': ref,
            })

    return inv_no, yr, mo, transactions

# Clear previous bad records
db.execute(text("DELETE FROM fuel_transaction WHERE source_doc_ref LIKE '3251%' AND entity_id=(SELECT id FROM entity WHERE code='VZC')"))
db.execute(text("DELETE FROM fuel_transaction WHERE source_doc_ref LIKE '3251%' AND entity_id=(SELECT id FROM entity WHERE code='KERA')"))
db.commit()
print('Cleared old VZC+KERA 325x records')

pdf_files = sorted(glob.glob('/Users/investimenti/Projects/nexus/data/vzc_phm_pdf/325*.pdf'))
print(f'Processing {len(pdf_files)} PDFs...\n')

total_ins = total_skip = total_unm = 0
for pdf_path in pdf_files:
    inv_no, yr, mo, txns = parse_pdf(pdf_path)
    inserted = 0
    for t in txns:
        if db.execute(text('SELECT id FROM fuel_transaction WHERE source_doc_ref=:r'), {'r': t['ref']}).fetchone():
            total_skip += 1; continue
        spz = resolve_card(t['card'])
        vid, eid = veh.get(spz, (None, None)) if spz else (None, None)
        if not eid: eid = VZC
        if not vid:
            # Ivanov = v9
            if 'IVANOV' in str(t['card']).upper():
                vid, eid = 'v9', VZC
            else:
                total_unm += 1
                if total_unm <= 5: print(f'  Unmatched: [{t["card"]}]')
                continue
        vendor = ((t['station'] + ' | ' + t['fuel']) if t['station'] and t['fuel'] else (t['fuel'] or t['station'] or ''))[:100]
        db.execute(text("INSERT INTO fuel_transaction (id,vehicle_id,entity_id,transaction_date,month,year,amount_total,liters_total,vendor_name,source_doc_ref,status,reviewed_at,created_at) VALUES (:id,:vid,:eid,:td,:mo,:yr,:amt,:lit,:vendor,:ref,'approved',:now,:now)"),
                   {'id': str(uuid.uuid4()), 'vid': vid, 'eid': eid, 'td': t['date'], 'mo': t['mo'], 'yr': t['yr'],
                    'amt': t['total'], 'lit': t['qty'], 'vendor': vendor, 'ref': t['ref'], 'now': now})
        inserted += 1; total_ins += 1
    print(f'{os.path.basename(pdf_path)}: {len(txns)} txn | +{inserted} | {mo:02d}/{yr}')

db.commit()
print(f'\nCELKEM: +{total_ins} | skip:{total_skip} | unmatched:{total_unm}')

# Update FORTIS cost records for VZC months
for yr_mo in db.execute(text("SELECT DISTINCT year, month FROM fuel_transaction WHERE entity_id=(SELECT id FROM entity WHERE code='VZC') ORDER BY year,month")).fetchall():
    yr2, mo2 = yr_mo
    groups = db.execute(text("SELECT vehicle_id, entity_id, ROUND(SUM(liters_total),2) l, ROUND(SUM(amount_total),2) kc, COUNT(*) cnt FROM fuel_transaction WHERE year=:yr AND month=:mo AND entity_id=(SELECT id FROM entity WHERE code='VZC') GROUP BY vehicle_id, entity_id"), {'yr': yr2, 'mo': mo2}).fetchall()
    for vid, eid, l, kc, cnt in groups:
        ex = db.execute(text("SELECT id FROM fortis_cost_record WHERE vehicle_id=:v AND period_year=:yr AND period_month=:mo AND cost_type='phm'"), {'v': vid, 'yr': yr2, 'mo': mo2}).fetchone()
        if ex:
            db.execute(text("UPDATE fortis_cost_record SET amount=:a, notes=:n WHERE id=:id"), {'a': float(kc or 0), 'n': f'Axigon VZC | {cnt}x | {float(l or 0):.1f} L', 'id': ex[0]})
        else:
            db.execute(text("INSERT INTO fortis_cost_record (id,entity_id,cost_type,period_year,period_month,vehicle_id,amount,currency,unit,notes,created_at) VALUES (:id,:eid,'phm',:yr,:mo,:vid,:amt,'CZK','Kc',:notes,:now)"),
                       {'id': str(uuid.uuid4()), 'eid': eid, 'yr': yr2, 'mo': mo2, 'vid': vid, 'amt': float(kc or 0), 'notes': f'Axigon VZC | {cnt}x | {float(l or 0):.1f} L', 'now': now})
db.commit()

# Final summary
print('\n=== PHM HOLDING – FINÁLNÍ PŘEHLED ===')
rows = db.execute(text("""
    SELECT e.code, ft.year, ft.month, COUNT(*) t,
           ROUND(SUM(ft.liters_total),0) l, ROUND(SUM(ft.amount_total),0) kc
    FROM fuel_transaction ft JOIN entity e ON e.id=ft.entity_id
    GROUP BY e.code, ft.year, ft.month ORDER BY ft.year, ft.month, e.code
""")).fetchall()

prev = None; gtl = gtk = 0
for r in rows:
    period = f'{r[1]}/{r[2]:02d}'
    if prev != period:
        if prev: print()
        prev = period
    l = float(r[4] or 0); k = float(r[5] or 0); gtl += l; gtk += k
    print(f'  {period}  {str(r[0]):8} {r[3]:3}x | {l:6.0f} L | {k:>10,.0f} Kc')

print(f'\n  CELKEM: {gtl:.0f} L | {gtk:,.0f} Kc')
print(f'  Transakcí: {db.execute(text("SELECT COUNT(*) FROM fuel_transaction")).scalar()}')
print(f'  FORTIS cost records: {db.execute(text("SELECT COUNT(*) FROM fortis_cost_record WHERE cost_type=\'phm\'")).scalar()}')
db.close()
