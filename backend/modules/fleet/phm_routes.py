from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.core.models.base import get_db
from backend.core.security.auth import get_current_user, CurrentUser
import os

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates"))
router = APIRouter(prefix="/fleet/phm", tags=["phm"])

def _txns(db, vid, yr, mo, dfrom, dto):
    rows = db.execute(text("SELECT ft.transaction_date, ft.liters_total, ft.amount_total, ft.vendor_name, ft.source_doc_ref FROM fuel_transaction ft WHERE ft.vehicle_id=:vid AND ft.year=:yr AND ft.month=:mo AND ft.transaction_date >= :dfrom AND (:dto IS NULL OR ft.transaction_date <= :dto) ORDER BY ft.transaction_date"), {"vid":vid,"yr":yr,"mo":mo,"dfrom":dfrom or "2000-01-01","dto":dto}).fetchall()
    return [{"datum":r[0],"lit":float(r[1] or 0),"kc":float(r[2] or 0),"vendor":str(r[3] or ""),"ref":str(r[4] or "")} for r in rows]

def _months(db, vid, dfrom, dto):
    rows = db.execute(text("SELECT ft.year, ft.month, COUNT(*), ROUND(SUM(ft.liters_total),1), ROUND(SUM(ft.amount_total),0) FROM fuel_transaction ft WHERE ft.vehicle_id=:vid AND ft.transaction_date >= :dfrom AND (:dto IS NULL OR ft.transaction_date <= :dto) GROUP BY ft.year, ft.month ORDER BY ft.year, ft.month"), {"vid":vid,"dfrom":dfrom or "2000-01-01","dto":dto}).fetchall()
    return [{"yr":r[0],"mo":r[1],"txn":r[2],"litry":float(r[3] or 0),"kc":float(r[4] or 0),"transactions":_txns(db,vid,r[0],r[1],dfrom,dto)} for r in rows]

def _vehicle_data(db, entity=None):
    rows = db.execute(text("SELECT v.id, v.spz, v.make||\' \'||v.model, e.code, COUNT(DISTINCT ft.id), ROUND(SUM(ft.liters_total),1), ROUND(SUM(ft.amount_total),0) FROM fuel_transaction ft JOIN vehicle v ON v.id=ft.vehicle_id JOIN entity e ON e.id=v.entity_id GROUP BY v.id ORDER BY SUM(ft.amount_total) DESC")).fetchall()
    result = []
    for r in rows:
        vid,spz,voz,ent,txn,lit,kc = r
        if entity and ent != entity: continue
        drv_rows = db.execute(text("SELECT p.id, p.first_name||\' \'||p.last_name, va.date_from, va.date_to, COUNT(DISTINCT ft.id), ROUND(SUM(ft.liters_total),1), ROUND(SUM(ft.amount_total),0) FROM vehicle_assignment va LEFT JOIN person p ON p.id=va.person_id LEFT JOIN fuel_transaction ft ON ft.vehicle_id=va.vehicle_id AND ft.transaction_date >= va.date_from AND (va.date_to IS NULL OR ft.transaction_date <= va.date_to) WHERE va.vehicle_id=:vid GROUP BY va.id ORDER BY va.date_from DESC"), {"vid":vid}).fetchall()
        drv_list = [{"person_id":d[0],"ridic":d[1] or "—","date_from":d[2],"date_to":d[3],"txn":d[4] or 0,"litry":float(d[5] or 0),"kc":float(d[6] or 0),"months":_months(db,vid,d[2],d[3])} for d in drv_rows]
        result.append({"veh_id":vid,"spz":spz or "—","vozidlo":voz,"entita":ent,"txn":txn,"litry":float(lit or 0),"kc":float(kc or 0),"drivers":drv_list})
    return result

def _person_data(db, entity=None):
    rows = db.execute(text("SELECT p.id, p.first_name||\' \'||p.last_name, e2.code, COUNT(DISTINCT ft.id), ROUND(SUM(ft.liters_total),1), ROUND(SUM(ft.amount_total),0) FROM vehicle_assignment va JOIN person p ON p.id=va.person_id JOIN fuel_transaction ft ON ft.vehicle_id=va.vehicle_id AND ft.transaction_date >= va.date_from AND (va.date_to IS NULL OR ft.transaction_date <= va.date_to) JOIN vehicle v ON v.id=va.vehicle_id JOIN entity e2 ON e2.id=v.entity_id GROUP BY p.id ORDER BY SUM(ft.amount_total) DESC")).fetchall()
    result = []
    for r in rows:
        pid,ridic,ent,txn,lit,kc = r
        if entity and ent != entity: continue
        veh_rows = db.execute(text("SELECT v.id, v.spz, v.make||\' \'||v.model, e.code, va.date_from, va.date_to, COUNT(DISTINCT ft.id), ROUND(SUM(ft.liters_total),1), ROUND(SUM(ft.amount_total),0) FROM vehicle_assignment va JOIN vehicle v ON v.id=va.vehicle_id JOIN entity e ON e.id=v.entity_id LEFT JOIN fuel_transaction ft ON ft.vehicle_id=va.vehicle_id AND ft.transaction_date >= va.date_from AND (va.date_to IS NULL OR ft.transaction_date <= va.date_to) WHERE va.person_id=:pid GROUP BY va.id ORDER BY va.date_from DESC"), {"pid":pid}).fetchall()
        veh_list = [{"veh_id":v[0],"spz":v[1] or "—","vozidlo":v[2],"entita":v[3],"date_from":v[4],"date_to":v[5],"txn":v[6] or 0,"litry":float(v[7] or 0),"kc":float(v[8] or 0),"months":_months(db,v[0],v[4],v[5])} for v in veh_rows]
        result.append({"person_id":pid,"ridic":ridic,"entita":ent,"txn":txn,"litry":float(lit or 0),"kc":float(kc or 0),"vehicles":veh_list})
    return result

@router.get("", response_class=HTMLResponse)
def phm_overview(request: Request, view: str = "vozidla", entity: str = None, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    data = _person_data(db, entity) if view == "lide" else _vehicle_data(db, entity)
    entities = db.execute(text("SELECT code FROM entity ORDER BY code")).scalars().all()
    return templates.TemplateResponse("pages/fleet/phm2.html", {"request":request,"current_user":current_user,"data":data,"view":view,"entity":entity,"total_kc":sum(d["kc"] for d in data),"total_lit":sum(d["litry"] for d in data),"total_txn":sum(d["txn"] for d in data),"entities":entities})
