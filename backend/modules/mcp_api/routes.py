"""NEXUS strojové JSON API (/api/v1/*).

Čistě JSON, autentizace přes API-key (ServiceToken) + scopes.
Tohle je povrch, který obaluje Nexus MCP server (mcp/nexus_mcp.py) a n8n.
HTML UI zůstává oddělené (cookie auth) — tady žádné šablony.
"""
import os
import subprocess
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.models.base import get_db
from backend.core.audit.log import audit
from backend.core.security.service_auth import require_scope, get_service_token
from backend.modules.mcp_api.models import ServiceToken, migrate

# zajisti tabulku service_token (idempotentní)
try:
    migrate()
except Exception:
    pass

router = APIRouter(prefix="/api/v1", tags=["api"])

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PYTHON = os.path.join(ROOT, ".venv", "bin", "python")


def _scalar(db: Session, sql: str, **params):
    """Bezpečný scalar dotaz — chyba (chybějící tabulka) → None."""
    try:
        return db.execute(text(sql), params).scalar()
    except Exception:
        return None


def _rows(db: Session, sql: str, **params) -> list[dict]:
    try:
        res = db.execute(text(sql), params)
        cols = res.keys()
        return [dict(zip(cols, r)) for r in res.fetchall()]
    except Exception:
        return []


# ── identita / health ───────────────────────────────────────────────────────
@router.get("/ping")
def ping(tok: ServiceToken = Depends(get_service_token)):
    return {"ok": True, "app": "nexus", "token": tok.name,
            "scopes": tok.scope_list(), "ts": datetime.utcnow().isoformat()}


# ── ATLAS KPI ───────────────────────────────────────────────────────────────
@router.get("/atlas/kpis")
def atlas_kpis(db: Session = Depends(get_db),
               tok: ServiceToken = Depends(require_scope("fortis:read"))):
    today = date.today()
    yr, mo = today.year, today.month
    pmo = mo - 1 if mo > 1 else 12
    pyr = yr if mo > 1 else yr - 1
    return {
        "period": {"year": yr, "month": mo},
        "headcount_active": _scalar(db, "SELECT COUNT(*) FROM person WHERE is_active=1"),
        "vehicles_active": _scalar(db, "SELECT COUNT(*) FROM vehicle WHERE status='ACTIVE'"),
        "phm_current": _scalar(db, "SELECT COALESCE(ROUND(SUM(amount_total),0),0) FROM fuel_transaction WHERE year=:y AND month=:m", y=yr, m=mo),
        "phm_prev": _scalar(db, "SELECT COALESCE(ROUND(SUM(amount_total),0),0) FROM fuel_transaction WHERE year=:y AND month=:m", y=pyr, m=pmo),
        "open_claims": _scalar(db, "SELECT COUNT(*) FROM insurance_claim WHERE status='pending'"),
        "open_fines": _scalar(db, "SELECT COUNT(*) FROM traffic_fine WHERE status NOT IN ('paid','dismissed')"),
        "open_deductions": _scalar(db, "SELECT COUNT(*) FROM deduction_case WHERE status='open'"),
        "notifications_new": _scalar(db, "SELECT COUNT(*) FROM notification WHERE status='new'"),
    }


# ── FLEET ───────────────────────────────────────────────────────────────────
@router.get("/fleet/vehicles")
def fleet_vehicles(limit: int = 200, status: str | None = None,
                   db: Session = Depends(get_db),
                   tok: ServiceToken = Depends(require_scope("fleet:read"))):
    sql = "SELECT id, spz, make, model, status, entity_id FROM vehicle"
    params = {}
    if status:
        sql += " WHERE status=:st"; params["st"] = status
    sql += " ORDER BY spz LIMIT :lim"; params["lim"] = max(1, min(limit, 1000))
    return {"vehicles": _rows(db, sql, **params)}


# ── PEOPLE ──────────────────────────────────────────────────────────────────
@router.get("/people")
def people(limit: int = 200, active_only: bool = True,
           db: Session = Depends(get_db),
           tok: ServiceToken = Depends(require_scope("people:read"))):
    sql = "SELECT id, first_name, last_name, email_work, phone, position, department, is_active FROM person"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY last_name LIMIT :lim"
    return {"people": _rows(db, sql, lim=max(1, min(limit, 2000)))}


# ── FORTIS (ekonomika) ──────────────────────────────────────────────────────
@router.get("/fortis/documents")
def fortis_documents(limit: int = 100, status: str | None = None, doc_type: str | None = None,
                     db: Session = Depends(get_db),
                     tok: ServiceToken = Depends(require_scope("fortis:read"))):
    sql = ("SELECT id, doc_type, source_system, doc_number, doc_date, due_date, "
           "amount_gross, currency, counterparty_name, status, paid_date "
           "FROM fortis_document")
    conds, params = [], {}
    if status:   conds.append("status=:st"); params["st"] = status
    if doc_type: conds.append("doc_type=:dt"); params["dt"] = doc_type
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY doc_date DESC LIMIT :lim"; params["lim"] = max(1, min(limit, 1000))
    return {"documents": _rows(db, sql, **params)}


# ── NOTIFICATIONS ───────────────────────────────────────────────────────────
@router.get("/notifications")
def list_notifications(limit: int = 50, status: str | None = None,
                       db: Session = Depends(get_db),
                       tok: ServiceToken = Depends(require_scope("notify:read"))):
    sql = "SELECT id, title, body, severity, status, related_type, created_at FROM notification"
    params = {}
    if status:
        sql += " WHERE status=:st"; params["st"] = status
    sql += " ORDER BY created_at DESC LIMIT :lim"; params["lim"] = max(1, min(limit, 500))
    return {"notifications": _rows(db, sql, **params)}


@router.post("/notifications")
def create_notification(payload: dict = Body(...),
                        db: Session = Depends(get_db),
                        tok: ServiceToken = Depends(require_scope("notify:write"))):
    """Vytvoří in-app notifikaci. Používá např. heal script při výpadku služby."""
    from backend.modules.notifications.models import Notification, NotificationDelivery
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title je povinný")
    n = Notification(
        title=title[:300],
        body=payload.get("body"),
        severity=payload.get("severity", "info"),
        related_type=payload.get("related_type", "general"),
        related_id=payload.get("related_id"),
        target_scope=payload.get("target_scope", "admin"),
        status="new",
        created_by=f"api:{tok.name}",
    )
    db.add(n); db.flush()
    db.add(NotificationDelivery(notification_id=n.id, channel="in_app",
                                delivery_status="sent", recipient="in_app"))
    db.commit()
    audit(db, action="create", resource_type="notification", resource_id=n.id,
          user_email=f"api:{tok.name}", detail=f"via api/v1: {title[:80]}")
    return {"ok": True, "id": n.id}


# ── MAIL (M365) ─────────────────────────────────────────────────────────────
@router.post("/mail/send")
def send_mail(payload: dict = Body(...),
              db: Session = Depends(get_db),
              tok: ServiceToken = Depends(require_scope("mail:send"))):
    to = payload.get("to")
    subject = payload.get("subject") or ""
    body = payload.get("body") or ""
    if not to:
        raise HTTPException(status_code=422, detail="'to' je povinný (string nebo list)")
    recipients = [a.strip() for a in to.split(",")] if isinstance(to, str) else list(to)
    recipients = [a for a in recipients if a]
    try:
        from backend.integrations.m365 import client as m365
        m365.send_mail(recipients, subject, body)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"M365 send selhal: {e}")
    audit(db, action="send", resource_type="mail", user_email=f"api:{tok.name}",
          detail=f"to={recipients} subj={subject[:60]}")
    return {"ok": True, "to": recipients}


# ── IMPORTY ─────────────────────────────────────────────────────────────────
_ALLOWED_IMPORTS = {"fleet": "scripts/import_fleet.py", "fuel": "scripts/import_fuel.py"}


@router.post("/imports/{name}/run")
def run_import(name: str,
               db: Session = Depends(get_db),
               tok: ServiceToken = Depends(require_scope("imports:run"))):
    script = _ALLOWED_IMPORTS.get(name)
    if not script:
        raise HTTPException(status_code=404, detail=f"Neznámý import '{name}'. Povolené: {list(_ALLOWED_IMPORTS)}")
    try:
        r = subprocess.run([PYTHON, script], cwd=ROOT,
                           env={**os.environ, "PYTHONPATH": ROOT},
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr)[-4000:]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import selhal: {e}")
    audit(db, action="run", resource_type="import", resource_id=name, user_email=f"api:{tok.name}")
    return {"ok": r.returncode == 0, "import": name, "output": out}
