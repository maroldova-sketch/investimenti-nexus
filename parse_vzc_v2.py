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
    clean = re.sub(r'\s+','',label.upper())
    for key, spz in [('SERGEYEV','1UT4267'),('VOZNIAK','1UN7000'),('LABORAT','9U59758'),('CITIGO','9U59758'),('KAROQ','1UT4267'),('1UN7393','1UN7393'),('1UN7000','1UN7000')]:
        if key in clean: return spz
    return None

def parse_pdf_v2(pdf_path):
    result = subprocess.run(['/opt/homebrew/bin/pdftotext', pdf_path, '-'], capture_output=True, text=True, timeout=15)
    text = result.stdout
    
    fname = os.path.basename(pdf_path)
    inv_no = fname.replace('faktura.pdf','').replace('.pdf','')
    
    # Extract period
    period_m = re.search(r'Fakturované období:\s*[\d]+\.\s*[\d]+\.\s*[\d]{4}\s*[-–]\s*(\d+)\.\s*(\d+)\.\s*(\d{4})', text)
    if period_m:
        yr = int(period_m.group(3)); mo = int(period_m.group(2))
    else:
        dm = re.search(r'Datum vystavení:\s*(\d{2})\.(\d{2})\.(\d{4})', text)
        yr = int(dm.group(3)) if dm else 2025
        mo = int(dm.group(2)) if dm else 6
    
    lines = text.split('\n')
    # Clean lines
    lines = [l.strip() for l in lines]
    
    transactions = []
    current_card = None
    i = 0
    
    def parse_num(s):
        s = s.strip().replace(' ','').replace(',','.')
        try: return float(s)
        except: return None
    
    while i < len(lines):
        line = lines[i]
        
        # Card header
        if line.startswith('ID karty:'):
            current_card = line.replace('ID karty:','').strip()
            # Also grab card number from next line if present
            i += 1
            continue
        
        # Transaction start: country code (CZ) followed by date
        if line == 'CZ' and current_card and i+2 < len(lines):
            date_str = lines[i+1]
            time_str = lines[i+2] if i+2 < len(lines) else ''
            receipt = lines[i+3] if i+3 < len(lines) else ''
            network = lines[i+4] if i+4 < len(lines) else ''
            # Skip empty
            if not re.match(r'\d{2}\.\d{2}\.\d{2}', date_str):
                i += 1; continue
            # Parse date
            dm = re.match(r'(\d{2})\.(\d{2})\.(\d{2,4})', date_str)
            if dm:
                d,m2,y = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
                if y < 100: y += 2000
                td = f'{y}-{m2:02d}-{d:02d}'
                txn_yr, txn_mo = y, m2
            else:
                td = f'{yr}-{mo:02d}-01'; txn_yr, txn_mo = yr, mo
            
            # Find station name, fuel type, qty, total in next ~12 lines
            station = ''; fuel = ''; qty = None; total = None
            j = i + 4
            nums_found = []
            while j < min(i+20, len(lines)):
                l2 = lines[j]
                # Station line (has Shell/Orlen/etc.)
                if any(w in l2 for w in ['Shell','Orlen','EuroOil','OMV','Benzina']) and not station:
                    j += 1
                    if j < len(lines) and re.match(r'\d+\s+', lines[j]):
                        station = lines[j]
                    else:
                        station = l2
                # Fuel type
                elif any(w in l2 for w in ['Natural','Nafta','CNG','Benzin','kapaliny','AdBlue']) and not fuel:
                    fuel = l2
                # Numbers
                elif re.match(r'^[\d ]+[,\.]\d{1,2}$', l2):
                    nums_found.append(parse_num(l2))
                # Stop at next card/transaction
                elif l2 == 'CZ' or l2.startswith('ID karty:') or l2.startswith('Číslo karty:'):
                    break
                j += 1
            
            # qty = first significant number, total = last number
            nums = [n for n in nums_found if n is not None and n > 0]
            if len(nums) >= 2:
                qty = nums[0]   # liters
                total = nums[-1]  # total with VAT
            elif len(nums) == 1:
                total = nums[0]
            
            ref = f'{inv_no}_{receipt}_{td}'
            
            transactions.append({
                'card': current_card,
                'date': td, 'yr': txn_yr, 'mo': txn_mo,
                'station': station, 'fuel': fuel,
                'qty': qty, 'total': total,
                'ref': ref,
            })
        
        i += 1
    
    return inv_no, yr, mo, transactions

# First clear bad data from previous parse attempt
deleted = db.execute(text("DELETE FROM fuel_transaction WHERE source_doc_ref LIKE '325%' AND entity_id = (SELECT id FROM entity WHERE code='VZC') AND year < 2026")).rowcount
db.commit()
print(f'Cleared {deleted} bad VZC 2025 records')

# Clear LOGPACK 2025 bad records too (0 liters)
deleted2 = db.execute(text("DELETE FROM fuel_transaction WHERE year < 2026 AND liters_total IS NULL AND entity_id = (SELECT id FROM entity WHERE code='LOGPACK')")).rowcount
db.commit()
print(f'Cleared {deleted2} bad LOGPACK 2025 zero-liter records')

pdf_files = sorted(glob.glob('/Users/investimenti/Projects/nexus/data/vzc_phm_pdf/325*.pdf'))
print(f'\nProcessing {len(pdf_files)} PDFs...\n')

total_ins = total_skip = total_unm = 0

for pdf_path in pdf_files:
    inv_no, yr, mo, txns = parse_pdf_v2(pdf_path)
    inserted = 0
    for t in txns:
        if db.execute(text('SELECT id FROM fuel_transaction WHERE source_doc_ref=:r'),{'r':t['ref']}).fetchone():
            total_skip += 1; continue
        spz = resolve_card(t['card'])
        vid, eid = veh.get(spz,(None,None)) if spz else (None,None)
        if not eid: eid = VZC
        if not vid:
            total_unm += 1
            if total_unm <= 5: print(f'  Unmatched: [{t["card"]}]')
            continue
        vendor = ((t['station']+' | '+t['fuel']) if t['station'] and t['fuel'] else (t['fuel'] or t['station'] or ''))[:100]
        db.execute(text("INSERT INTO fuel_transaction (id,vehicle_id,entity_id,transaction_date,month,year,amount_total,liters_total,vendor_name,source_doc_ref,status,reviewed_at,created_at) VALUES (:id,:vid,:eid,:td,:mo,:yr,:amt,:lit,:vendor,:ref,'approved',:now,:now)"),
                   {'id':str(uuid.uuid4()),'vid':vid,'eid':eid,'td':t['date'],'mo':t['mo'],'yr':t['yr'],
                    'amt':t['total'],'lit':t['qty'],'vendor':vendor,'ref':t['ref'],'now':now})
        inserted += 1; total_ins += 1
    print(f'{os.path.basename(pdf_path)}: {len(txns)} parsed | +{inserted} | {mo:02d}/{yr}')

db.commit()
print(f'\nCELKEM: +{total_ins} | skip:{total_skip} | unmatched:{total_unm}')

print('\n=== PHM přehled ===')
rows = db.execute(text("""
    SELECT e.code, ft.year, ft.month, COUNT(*) t,
           ROUND(SUM(ft.liters_total),0) l, ROUND(SUM(ft.amount_total),0) kc
    FROM fuel_transaction ft JOIN entity e ON e.id=ft.entity_id
    GROUP BY e.code, ft.year, ft.month ORDER BY e.code, ft.year, ft.month
""")).fetchall()
gtl=gtk=0
for r in rows:
    l=float(r[4] or 0); k=float(r[5] or 0); gtl+=l; gtk+=k
    print(f'  {str(r[0]):8} {r[1]}/{r[2]:02d} | {r[3]:3}x | {l:.0f}L | {k:,.0f} Kc')
print(f'  CELKEM: {gtl:.0f} L | {gtk:,.0f} Kc')
print(f'\nCelkem: {db.execute(text("SELECT COUNT(*) FROM fuel_transaction")).scalar()} txn')
db.close()
