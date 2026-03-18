import uuid
from datetime import datetime
from sqlalchemy import text
import sys
sys.path.insert(0, '/Users/investimenti/Projects/nexus')
from backend.core.models.base import SessionLocal

db = SessionLocal()
now = datetime.now()
entities = {r[0]: r[1] for r in db.execute(text('SELECT code, id FROM entity')).fetchall()}
LOGPACK = entities['LOGPACK']
KERA = entities['KERA']

archiv_pdfs = [
    ('3251147043', KERA, '2025-05-01', 'Axigon KERA 05/2025 1.pol'),
    ('3251153515', KERA, '2025-06-01', 'Axigon KERA 06/2025 1.pol'),
    ('3251157652', KERA, '2025-07-01', 'Axigon KERA 07/2025 1.pol'),
    ('3251164407', KERA, '2025-07-15', 'Axigon KERA 07/2025 2.pol'),
    ('3251166948', KERA, '2025-08-01', 'Axigon KERA 08/2025 1.pol'),
    ('3251172939', KERA, '2025-08-15', 'Axigon KERA 08/2025 2.pol'),
    ('3251175734', KERA, '2025-09-01', 'Axigon KERA 09/2025 1.pol'),
    ('3251183087', KERA, '2025-09-15', 'Axigon KERA 09/2025 2.pol'),
    ('3251186833', KERA, '2025-10-01', 'Axigon KERA 10/2025 1.pol'),
    ('3251191453', KERA, '2025-10-15', 'Axigon KERA 10/2025 2.pol'),
    ('3251195737', KERA, '2025-11-01', 'Axigon KERA 11/2025 1.pol'),
    ('3251200532', KERA, '2025-11-15', 'Axigon KERA 11/2025 2.pol'),
    ('3251209099', KERA, '2025-12-01', 'Axigon KERA 12/2025 1.pol'),
    ('3251209760', KERA, '2025-12-15', 'Axigon KERA 12/2025 2.pol'),
    ('3251218336', KERA, '2026-01-02', 'Axigon KERA 01/2026 1.pol'),
    ('3251902288', LOGPACK, '2025-11-03', 'Axigon LOGPACK 11/2025'),
    ('3251902516', LOGPACK, '2025-12-01', 'Axigon LOGPACK 12/2025'),
    ('6025000324', LOGPACK, '2025-05-06', 'Axigon LOGPACK doklad 05/2025'),
]

added = updated = 0
for inv_no, eid, doc_date, desc in archiv_pdfs:
    ref = 'archiv_2025/' + inv_no + 'faktura.pdf'
    ex = db.execute(text('SELECT id FROM fortis_document WHERE source_ref=:r OR doc_number=:dn'), {'r': ref, 'dn': inv_no}).fetchone()
    if ex:
        db.execute(text('UPDATE fortis_document SET doc_date=:dd, description=:d, entity_id=:eid WHERE id=:id'), {'dd': doc_date, 'd': desc, 'eid': eid, 'id': ex[0]})
        updated += 1
    else:
        db.execute(text("INSERT INTO fortis_document (id,entity_id,doc_type,source_system,source_ref,doc_date,doc_number,currency,counterparty_name,description,status,created_at,updated_at) VALUES (:id,:eid,'invoice_in','axigon',:ref,:dd,:dn,'CZK','AXIGON a.s.',:desc,'imported',:now,:now)"), {'id': str(uuid.uuid4()), 'eid': eid, 'ref': ref, 'dd': doc_date, 'dn': inv_no, 'desc': desc, 'now': now})
        added += 1

db.commit()
print(f'Archiv 2025: {added} added | {updated} updated')
rows = db.execute(text("SELECT source_system, COUNT(*) cnt FROM fortis_document GROUP BY source_system ORDER BY cnt DESC")).fetchall()
for r in rows:
    print(f'  {str(r[0]):20} {r[1]}')
total_fd = db.execute(text('SELECT COUNT(*) FROM fortis_document')).scalar()
total_fc = db.execute(text('SELECT COUNT(*) FROM fortis_cost_record')).scalar()
total_ft = db.execute(text('SELECT COUNT(*) FROM fuel_transaction')).scalar()
print(f'Celkem: {total_fd} docs | {total_fc} cost records | {total_ft} PHM txn')
db.close()
