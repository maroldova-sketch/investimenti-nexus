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
from backend.modules.notifications.routes import router as notifications_router
from backend.modules.fleet.trip_routes import router as trip_router

app = FastAPI(title="NEXUS", redirect_slashes=False, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

app.include_router(auth_router)
app.include_router(fleet_router)
app.include_router(people_router)
app.include_router(attendance_router)
app.include_router(staging_router)
app.include_router(trip_router)
app.include_router(notifications_router)
app.include_router(deduction_router)
app.include_router(driver_router)

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

@app.get("/import/run/fleet", response_class=PlainTextResponse)
def run_fleet():
    r = subprocess.run([PYTHON, "scripts/import_fleet.py"], cwd=ROOT,
        env={**os.environ, "PYTHONPATH": ROOT}, capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr) + "\n\nDone. Go to /import"

@app.get("/import/run/fuel", response_class=PlainTextResponse)
def run_fuel():
    r = subprocess.run([PYTHON, "scripts/import_fuel.py"], cwd=ROOT,
        env={**os.environ, "PYTHONPATH": ROOT}, capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr) + "\n\nDone. Go to /import"
