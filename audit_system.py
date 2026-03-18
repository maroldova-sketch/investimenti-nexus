import sys
sys.path.insert(0, '.')
from sqlalchemy import text
from backend.core.models.base import SessionLocal
import json, urllib.request

db = SessionLocal()

def q(sql): return db.execute(text(sql)).fetchall()
def s(sql): return db.execute(text(sql)).scalar()

print("=== NEXUS SYSTEM AUDIT ===")
print()

print("== ENTITIES ==")
for r in q("SELECT code,division,parent_id,ico FROM entity ORDER BY division,code"):
    print(f"  {r[0]:10} div={r[1]} parent={str(r[2] or 'root')[:8]} ico={r[3]}")

print()
print("== PERSONS ==")
total,active = s("SELECT COUNT(*) FROM person"), s("SELECT COUNT(*) FROM person WHERE is_active=1")
print(f"  Celkem: {total} | Aktivni: {active} | Neaktivni: {total-active}")

print()
print("== VEHICLES ==")
for r in q("SELECT status,COUNT(*) FROM vehicle GROUP BY status"):
    print(f"  {r[0]:15} {r[1]}")
print(f"  Bez SPZ: {s('SELECT COUNT(*) FROM vehicle WHERE spz IS NULL')}")

print()
print("== VOZIDLA + RIDICI ==")
for r in q("SELECT v.spz,v.make,v.model,v.status,e.code FROM vehicle v JOIN entity e ON e.id=v.entity_id ORDER BY e.code,v.spz"):
    va = db.execute(text("SELECT p.first_name||' '||p.last_name FROM vehicle_assignment va JOIN person p ON p.id=va.person_id WHERE va.vehicle_id=(SELECT id FROM vehicle WHERE spz=:spz) AND va.date_to IS NULL LIMIT 1"), {"spz": r[0]}).scalar()
    print(f"  {str(r[0] or '?SPZ'):12} {str(r[1]):8} {str(r[2])[:20]:20} {r[3]:10} {r[4]:8} ridic={str(va or '---')}")

print()
print("== FUEL TRANSACTIONS BY MONTH ==")
grand_l, grand_kc = 0, 0
for r in q("SELECT year,month,COUNT(*),ROUND(SUM(liters_total),0),ROUND(SUM(amount_total),0) FROM fuel_transaction GROUP BY year,month ORDER BY year,month"):
    l,k = float(r[3] or 0), float(r[4] or 0)
    grand_l += l; grand_kc += k
    print(f"  {r[0]}/{r[1]:02d}  {r[2]:3}x  {l:6.0f}L  {k:9,.0f} Kc")
print(f"  CELKEM:       {s('SELECT COUNT(*) FROM fuel_transaction'):3}x  {grand_l:6.0f}L  {grand_kc:9,.0f} Kc")

print()
print("== FUEL BY ENTITY ==")
for r in q("SELECT e.code,COUNT(*),ROUND(SUM(ft.liters_total),0),ROUND(SUM(ft.amount_total),0) FROM fuel_transaction ft JOIN entity e ON e.id=ft.entity_id GROUP BY e.code ORDER BY SUM(ft.amount_total) DESC"):
    print(f"  {r[0]:8}  {r[1]:3}x  {float(r[2] or 0):6.0f}L  {float(r[3] or 0):9,.0f} Kc")

print()
print("== FUEL QUALITY CHECK ==")
print(f"  Bez liters_total: {s('SELECT COUNT(*) FROM fuel_transaction WHERE liters_total IS NULL OR liters_total=0')}")
print(f"  Bez amount_total: {s('SELECT COUNT(*) FROM fuel_transaction WHERE amount_total IS NULL OR amount_total=0')}")
print(f"  Bez vehicle link: {s('SELECT COUNT(*) FROM fuel_transaction WHERE vehicle_id IS NULL')}")

print()
print("== INSURANCE CLAIMS ==")
for r in q("SELECT v.spz,ic.status,ic.invoice_amount,ic.settlement_amount,ic.policy_number FROM insurance_claim ic LEFT JOIN vehicle v ON v.id=ic.vehicle_id ORDER BY v.spz"):
    print(f"  {str(r[0] or '?'):12} status={r[1]:10} faktura={float(r[2] or 0):8,.0f} plneni={str(r[3] or '?')} pol={r[4]}")

print()
print("== TRAFFIC FINES ==")
for r in q("SELECT v.spz,tf.status,tf.amount FROM traffic_fine tf LEFT JOIN vehicle v ON v.id=tf.vehicle_id"):
    print(f"  {str(r[0] or '?'):12} status={r[1]} amount={float(r[2] or 0):,.0f}")

print()
print("== DEDUCTION CASES ==")
for r in q("SELECT dc.status,dc.amount,p.first_name||' '||p.last_name FROM deduction_case dc LEFT JOIN person p ON p.id=dc.person_id"):
    print(f"  status={r[0]:10} amount={float(r[1] or 0):,.0f} osoba={r[2]}")

print()
print("== FORTIS DOCUMENTS ==")
for r in q("SELECT source_system,COUNT(*) FROM fortis_document GROUP BY source_system ORDER BY COUNT(*) DESC"):
    print(f"  {r[0]:20} {r[1]}")
print(f"  Bez total_amount: {s('SELECT COUNT(*) FROM fortis_document WHERE total_amount IS NULL')}")

print()
print("== FORTIS COST RECORDS ==")
for r in q("SELECT cost_type,COUNT(*),ROUND(SUM(amount),0) FROM fortis_cost_record GROUP BY cost_type"):
    print(f"  {r[0]:20} {r[1]:3}x  {float(r[2] or 0):9,.0f} Kc")

print()
print("== FORTIS PAYROLL SUMMARY ==")
total_gross = total_cost = 0
for r in q("SELECT e.code,period_year,period_month,COUNT(*),ROUND(SUM(gross_wage),0),ROUND(SUM(employer_total_cost),0) FROM fortis_payroll_summary fps JOIN entity e ON e.id=fps.entity_id GROUP BY e.code,period_year,period_month ORDER BY period_year,period_month,e.code"):
    g,c = float(r[4] or 0), float(r[5] or 0)
    total_gross += g; total_cost += c
    print(f"  {r[0]:8} {r[1]}/{r[2]:02d} {r[3]:2}os  hruba={g:9,.0f}  naklad={c:9,.0f}")
print(f"  CELKEM:  {s('SELECT COUNT(*) FROM fortis_payroll_summary')}os  hruba={total_gross:,.0f}  naklad={total_cost:,.0f}")
print(f"  Bez person_id linku: {s('SELECT COUNT(*) FROM fortis_payroll_summary WHERE person_id IS NULL')}")

print()
print("== EMPLOYMENT CONTRACTS ==")
print(f"  Celkem: {s('SELECT COUNT(*) FROM employment_contract')} | Aktivnich: {s('SELECT COUNT(*) FROM employment_contract WHERE is_active=1')}")

print()
print("== ATTENDANCE ==")
print(f"  Periody: {s('SELECT COUNT(*) FROM attendance_period')}")
print(f"  Submissions: {s('SELECT COUNT(*) FROM attendance_submission')}")

print()
print("== AUDIT LOG ==")
print(f"  Celkem zaznamu: {s('SELECT COUNT(*) FROM audit_log')}")
for r in q("SELECT action,COUNT(*) FROM audit_log GROUP BY action ORDER BY COUNT(*) DESC LIMIT 8"):
    print(f"  {r[0]:30} {r[1]}")

print()
print("== API ROUTES ==")
try:
    resp = urllib.request.urlopen("http://localhost:8000/openapi.json", timeout=3)
    api = json.load(resp)
    for p in sorted(api["paths"].keys()):
        print(f"  {p}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("== GIT TAGS ==")
import subprocess
r = subprocess.run(["git","tag","--sort=-version:refname"], capture_output=True, text=True, cwd="/Users/investimenti/Projects/nexus")
print(f"  {r.stdout.strip()}")

db.close()
