import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, PlainTextResponse
import subprocess

from backend.modules.auth.routes import router as auth_router
from backend.modules.fleet.routes import router as fleet_router
from backend.modules.people.routes import router as people_router
from backend.modules.attendance.routes import router as attendance_router
from backend.modules.staging.routes import router as staging_router
from backend.modules.fleet.driver_routes import router as driver_router
from backend.modules.fleet.deduction_routes import router as deduction_router
from backend.modules.fleet.completion_routes import router as completion_router
from backend.modules.notifications.routes import router as notifications_router
from backend.modules.fleet.trip_routes import router as trip_router
from backend.modules.fleet.phm_routes import router as phm2_router
from backend.modules.axigon.routes import router as axigon_router
from backend.modules.people.calendar_routes import router as calendar_router
from backend.modules.people.merge_routes import router as merge_router
from backend.modules.people.contract_routes import router as contract_router
from backend.modules.webhooks.routes import router as webhook_router
from backend.modules.atlas.routes import router as atlas_router
from backend.modules.gov.routes import router as gov_router
from backend.modules.m365.routes import router as m365_router
from backend.modules.mcp_api.routes import router as api_router
from backend.modules.idoklad.routes import router as idoklad_router

app = FastAPI(title="NEXUS", redirect_slashes=False, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(notifications_router)
app.include_router(axigon_router)
app.include_router(completion_router)
app.include_router(deduction_router)
app.include_router(driver_router)
app.include_router(fleet_router)
app.include_router(merge_router)
app.include_router(contract_router)
app.include_router(people_router)
app.include_router(attendance_router)
app.include_router(staging_router)
app.include_router(trip_router)
app.include_router(atlas_router)
app.include_router(phm2_router)
app.include_router(gov_router)
app.include_router(m365_router)
app.include_router(api_router)
app.include_router(idoklad_router)

@app.get("/")
def root(): return RedirectResponse("/fleet")

@app.get("/health")
def health(): return {"status": "ok", "app": "nexus"}

@app.get("/health/db")
def health_db():
    from backend.core.models.base import SessionLocal
    try:
        db = SessionLocal(); db.execute(__import__('sqlalchemy').text("SELECT 1")); db.close()
        return {"status": "ok", "db": "sqlite"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# Quick import triggers
ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(ROOT, ".venv", "bin", "python")

from fastapi import Depends, HTTPException
from backend.core.security.service_auth import require_human_or_service

# GAP 0 fix: import trigger jako POST (ne CSRF-able GET) + auth (uživatel/API-key).
# Distinct path /import/trigger/{name} — nešadowuje se staging routou /import/{batch_id}/...
_IMPORT_SCRIPTS = {"fleet": "scripts/import_fleet.py", "fuel": "scripts/import_fuel.py"}

@app.post("/import/trigger/{name}", response_class=PlainTextResponse)
def import_trigger(name: str, _auth: dict = Depends(require_human_or_service)):
    script = _IMPORT_SCRIPTS.get(name)
    if not script:
        raise HTTPException(status_code=404, detail=f"Neznámý import '{name}'")
    r = subprocess.run([PYTHON, script], cwd=ROOT,
        env={**os.environ, "PYTHONPATH": ROOT}, capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr) + "\n\nDone. Go to /import"
