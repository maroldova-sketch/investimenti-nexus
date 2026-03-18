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
    # Direct SPZ
    m = re.search(r'\b([0-9][A-Z0-9]{6,8})\b', label)
    if m: return m.group(1)
    clean = re.sub(r'\s+','',label.upper())
    for key, spz in [('SERGEYEV','1UT4267'),('VOZNIAK','1UN7000'),('LABORAT','9U59758'),('CITIGO','9U59758'),('KAROQ','1UT4267')]:
        if key in clean: return spz
    return None

def parse_pdf(pdf_path):
    result = subprocess.run(['/opt/homebrew/bin/pdftotext', pdf_path, '-'], capture_output=True, text=True, timeout=15)
    text = result.stdout
    lines = text.split('\n')
    
    # Extract invoice number from filename
    fname = os.path.basename(pdf_path)
    inv_no = fname.replace('faktura.pdf','').replace('.pdf','')
    
    # Extract period from header
    period_m = re.search(r'Fakturované období:\s*(\d+)\.\s*(\d+)\.\s*(\d{4})\s*[-–]\s*(\d+)\.\s*(\d+)\.\s*(\d{4})', text)
    if period_m:
        yr = int(period_m.group(6))
        mo = int(period_m.group(5))
    else:
        # Fallback: datum vystaveni
        date_m = re.search(r'Datum vystavení:\s*(\d{2})\.(\d{2})\.(\d{4})', text)
        if date_m:
            yr = int(date_m.group(3))
            mo = int(date_m.group(2))
        else:
            yr, mo = 2025, 6  # fallback
    
    # Parse transactions
    # Pattern: ID karty block -> transactions below
    transactions = []
    i = 0
    current_card = None
    
    while i < len(lines):
        line = lines[i].strip()
        
        # New card
        if line.startswith('ID karty:'):
            current_card = line.replace('ID karty:','').strip()
            i += 1
            continue
        
        # Transaction line: CZ\n date\n time\n receipt\n network\n place\n fuel\n qty\n price_before\n price_after\n vat\n vat_czk\n netto\n total
        if line == 'CZ' and current_card:
            try:
                # Read following lines
                date_str = lines[i+1].strip() if i+1 < len(lines) else ''
                time_str = lines[i+2].strip() if i+2 < len(lines) else ''
                receipt = lines[i+3].strip() if i+3 < len(lines) else ''
                network = lines[i+4].strip() if i+4 < len(lines) else ''
                place = lines[i+5].strip() if i+5 < len(lines) else ''
                fuel = lines[i+6].strip() if i+6 < len(lines) else ''
                qty_str = lines[i+7].strip() if i+7 < len(lines) else ''
                # Skip unit price lines, find total
                # qty is float, then price_before, price_after, vat%, dph, netto, total
                # We need: qty, total (Celkem Kč)
                
                # Parse date
                dm = re.match(r'(\d{2})\.(\d{2})\.(\d{2,4})', date_str)
                if dm:
                    d,m2,y = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
                    if y < 100: y += 2000
                    td = f'{y}-{m2:02d}-{d:02d}'
                    txn_yr, txn_mo = y, m2
                else:
                    td = f'{yr}-{mo:02d}-01'
                    txn_yr, txn_mo = yr, mo
                
                qty = float(qty_str.replace(',','.').replace(' ','')) if re.match(r'[\d,\. ]+$', qty_str) else None
                
                # Find total amount: scan forward for last number before next CZ or card block
                total = None
                for j in range(i+8, min(i+20, len(lines))):
                    l2 = lines[j].strip()
                    # Number with CZK format
                    nm = re.match(r'^([\d ]+[,\.]\d{1,2})$', l2)
                    if nm:
                        total = float(nm.group(1).replace(' ','').replace(',','.'))
                
                if fuel and td:
                    spz = resolve_card(current_card)
                    transactions.append({
                        'spz': spz,
                        'card_label': current_card,
                        'date': td,
                        'yr': txn_yr,
                        'mo': txn_mo,
                        'fuel': fuel,
                        'qty': qty,
                        'total': total,
                        'station': place,
                        'receipt': f'{inv_no}_{receipt}',
                        'inv_no': inv_no,
                    })
            except Exception as e:
                pass
        i += 1
    
    return inv_no, yr, mo, transactions

# Process all PDFs
pdf_files = sorted(glob.glob('/Users/investimenti/Projects/nexus/data/vzc_phm_pdf/325*.pdf'))
print(f'Processing {len(pdf_files)} PDFs...')

total_ins = total_skip = total_unm = 0

for pdf_path in pdf_files:
    inv_no, yr, mo, txns = parse_pdf(pdf_path)
    print(f'\n{os.path.basename(pdf_path)}: {len(txns)} txn | {mo:02d}/{yr}')
    
    inserted = 0
    for t in txns:
        ref = t['receipt']
        if db.execute(text('SELECT id FROM fuel_transaction WHERE source_doc_ref=:r'),{'r':ref}).fetchone():
            total_skip += 1; continue
        
        spz = t['spz']
        vid, eid = veh.get(spz,(None,None)) if spz else (None,None)
        if not eid: eid = VZC
        
        if not vid:
            total_unm += 1
            if total_unm <= 5:
                print(f'  Unmatched: [{t["card_label"]}] spz={spz}')
            continue
        
        db.execute(text("INSERT INTO fuel_transaction (id,vehicle_id,entity_id,transaction_date,month,year,amount_total,liters_total,vendor_name,source_doc_ref,status,reviewed_at,created_at) VALUES (:id,:vid,:eid,:td,:mo,:yr,:amt,:lit,:vendor,:ref,'approved',:now,:now)"),
                   {'id':str(uuid.uuid4()),'vid':vid,'eid':eid,'td':t['date'],'mo':t['mo'],'yr':t['yr'],
                    'amt':t['total'],'lit':t['qty'],
                    'vendor':(t['station']+' | '+t['fuel'])[:100] if t['station'] else t['fuel'][:100],
                    'ref':ref,'now':now})
        inserted += 1
        total_ins += 1
    
    print(f'  +{inserted} inserted')

db.commit()
print(f'\nCELKEM: +{total_ins} | skip:{total_skip} | unmatched:{total_unm}')

# Summary
print('\n=== PHM přehled po entitách a měsících ===')
rows = db.execute(text("""
    SELECT e.code, ft.year, ft.month, COUNT(DISTINCT ft.vehicle_id) v, COUNT(*) t,
           ROUND(SUM(ft.liters_total),0) l, ROUND(SUM(ft.amount_total),0) kc
    FROM fuel_transaction ft JOIN entity e ON e.id=ft.entity_id
    GROUP BY e.code, ft.year, ft.month ORDER BY e.code, ft.year, ft.month
""")).fetchall()
gtl=gtk=0
for r in rows:
    l=float(r[5] or 0); k=float(r[6] or 0); gtl+=l; gtk+=k
    print(f'  {str(r[0]):8} {r[1]}/{r[2]:02d} | {r[3]} voz | {r[4]:3}x | {l:.0f} L | {k:,.0f} Kc')
print(f'  CELKEM: {gtl:.0f} L | {gtk:,.0f} Kc')
total = db.execute(text('SELECT COUNT(*) FROM fuel_transaction')).scalar()
print(f'\n{total} PHM transakcí celkem')
db.close()
