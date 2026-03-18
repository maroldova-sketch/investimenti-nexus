from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.core.models.base import get_db
from backend.core.security.auth import get_current_user, CurrentUser
import os
from datetime import date

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '../../..', 'frontend', 'templates'))
router = APIRouter(prefix='/atlas', tags=['atlas'])

def _get_kpis(db):
    today = date.today()
    cur_yr, cur_mo = today.year, today.month
    prev_mo = cur_mo - 1 if cur_mo > 1 else 12
    prev_yr = cur_yr if cur_mo > 1 else cur_yr - 1

    hc = db.execute(text('SELECT COUNT(*) FROM person WHERE is_active=1')).scalar()

    phm_cur = float(db.execute(text('SELECT COALESCE(ROUND(SUM(amount_total),0),0) FROM fuel_transaction WHERE year=:yr AND month=:mo'), {'yr':cur_yr,'mo':cur_mo}).scalar() or 0)
    phm_prev = float(db.execute(text('SELECT COALESCE(ROUND(SUM(amount_total),0),0) FROM fuel_transaction WHERE year=:yr AND month=:mo'), {'yr':prev_yr,'mo':prev_mo}).scalar() or 0)

    pay = db.execute(text('SELECT e.code, ROUND(SUM(fps.gross_wage),0), ROUND(SUM(fps.employer_total_cost),0), COUNT(*) FROM fortis_payroll_summary fps JOIN entity e ON e.id=fps.entity_id WHERE fps.period_year=:yr AND fps.period_month=:mo GROUP BY e.code ORDER BY e.code'), {'yr':cur_yr,'mo':prev_mo}).fetchall()
    if not pay:
        pay = db.execute(text('SELECT e.code, ROUND(SUM(fps.gross_wage),0), ROUND(SUM(fps.employer_total_cost),0), COUNT(*) FROM fortis_payroll_summary fps JOIN entity e ON e.id=fps.entity_id WHERE fps.period_year=:yr AND fps.period_month=:mo GROUP BY e.code ORDER BY e.code'), {'yr':prev_yr,'mo':prev_mo}).fetchall()
    p_gross = sum(float(r[1] or 0) for r in pay)
    p_emp = sum(float(r[2] or 0) for r in pay)
    p_by_ent = [{'code':r[0],'gross':float(r[1] or 0),'cost':float(r[2] or 0),'cnt':r[3]} for r in pay]

    open_claims = db.execute(text('SELECT COUNT(*) FROM insurance_claim WHERE status=:s'), {'s':'pending'}).scalar() or 0
    open_fines = db.execute(text('SELECT COUNT(*) FROM traffic_fine WHERE status NOT IN (:s1,:s2)'), {'s1':'paid','s2':'dismissed'}).scalar() or 0
    open_deductions = db.execute(text('SELECT COUNT(*) FROM deduction_case WHERE status=:s'), {'s':'open'}).scalar() or 0
    v_act = db.execute(text('SELECT COUNT(*) FROM vehicle WHERE status=:s'), {'s':'ACTIVE'}).scalar() or 0

    phm_ent = db.execute(text('SELECT e.code, ROUND(SUM(ft.amount_total),0), ROUND(SUM(ft.liters_total),0), COUNT(*) FROM fuel_transaction ft JOIN entity e ON e.id=ft.entity_id WHERE ft.year=:yr AND ft.month=:mo GROUP BY e.code ORDER BY SUM(ft.amount_total) DESC'), {'yr':cur_yr,'mo':cur_mo}).fetchall()
    if not phm_ent:
        phm_ent = db.execute(text('SELECT e.code, ROUND(SUM(ft.amount_total),0), ROUND(SUM(ft.liters_total),0), COUNT(*) FROM fuel_transaction ft JOIN entity e ON e.id=ft.entity_id WHERE ft.year=:yr AND ft.month=:mo GROUP BY e.code ORDER BY SUM(ft.amount_total) DESC'), {'yr':prev_yr,'mo':prev_mo}).fetchall()

    trend = list(reversed(db.execute(text('SELECT year, month, ROUND(SUM(amount_total),0) FROM fuel_transaction GROUP BY year, month ORDER BY year DESC, month DESC LIMIT 11')).fetchall()))

    return {
        'headcount': hc, 'phm_cur': phm_cur, 'phm_prev': phm_prev,
        'phm_delta_pct': round((phm_cur - phm_prev) / max(phm_prev, 1) * 100, 1),
        'payroll_gross': p_gross, 'payroll_emp': p_emp, 'payroll_by_entity': p_by_ent,
        'payroll_month': f'{prev_mo:02d}/{cur_yr if cur_mo > 1 else prev_yr}',
        'open_claims': open_claims, 'open_fines': open_fines, 'open_deductions': open_deductions,
        'vehicles_active': v_act,
        'phm_by_entity': [{'code':r[0],'kc':float(r[1] or 0),'lit':float(r[2] or 0),'txn':r[3]} for r in phm_ent],
        'phm_trend': [{'yr':r[0],'mo':r[1],'kc':float(r[2] or 0)} for r in trend],
        'period': f'{cur_mo:02d}/{cur_yr}',
    }

@router.get('', response_class=HTMLResponse)
def atlas_dashboard(request: Request, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return templates.TemplateResponse('pages/atlas/dashboard.html', {'request':request,'current_user':current_user,**_get_kpis(db)})

@router.get('/api/kpis', response_class=JSONResponse)
def atlas_kpis_api(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return _get_kpis(db)
