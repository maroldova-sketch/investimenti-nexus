from sqlalchemy import text
import sys
sys.path.insert(0, '/Users/investimenti/Projects/nexus')
from backend.core.models.base import SessionLocal
db = SessionLocal()

rows = db.execute(text("""
    SELECT
        v.spz,
        v.make || ' ' || v.model as vozidlo,
        e.code as entita,
        p.first_name || ' ' || p.last_name as ridic,
        ft.year, ft.month,
        COUNT(*) txn,
        ROUND(SUM(ft.liters_total),1) litry,
        ROUND(SUM(ft.amount_total),0) kc
    FROM fuel_transaction ft
    JOIN vehicle v ON v.id = ft.vehicle_id
    JOIN entity e ON e.id = v.entity_id
    LEFT JOIN vehicle_assignment va ON va.vehicle_id = v.id AND va.date_to IS NULL
    LEFT JOIN person p ON p.id = va.person_id
    GROUP BY v.id, ft.year, ft.month
    ORDER BY v.spz NULLS LAST, ft.year, ft.month
""")).fetchall()

for r in rows:
    print('|'.join(str(x) for x in r))
db.close()
