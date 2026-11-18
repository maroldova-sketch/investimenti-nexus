import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, PlainTextResponse

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

app = FastAPI(title="NEXUS", redirect_slashes=False, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

fleet_dependencies = []
app.state.fleet_pilot_enabled = False
if os.environ.get("NEXUS_FLEET_ELIAS_ENABLED") == "1":
    from backend.modules.fleet.pilot import install as install_fleet_pilot
    fleet_dependencies = install_fleet_pilot(app)

app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(notifications_router)
app.include_router(axigon_router, dependencies=fleet_dependencies)
app.include_router(completion_router, dependencies=fleet_dependencies)
app.include_router(deduction_router, dependencies=fleet_dependencies)
app.include_router(driver_router, dependencies=fleet_dependencies)
# Literal fleet paths must precede /fleet/{vehicle_id}.
app.include_router(trip_router, dependencies=fleet_dependencies)
app.include_router(phm2_router, dependencies=fleet_dependencies)
app.include_router(fleet_router, dependencies=fleet_dependencies)
app.include_router(merge_router)
app.include_router(contract_router)
# Keep the constant /people/hr route before /people/{person_id}.
# Schema installation is an explicit separate step, never a startup mutation.
app.state.hr_enabled = False
if os.environ.get("NEXUS_HR_ENABLED") == "1":
    from backend.modules.hr import install as install_hr
    install_hr(app)
app.include_router(people_router)
app.include_router(attendance_router)
app.include_router(atlas_router)
app.include_router(gov_router)
app.include_router(m365_router)

@app.get("/")
def root(): return RedirectResponse("/fleet/operations" if app.state.fleet_pilot_enabled else "/fleet")

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

@app.get("/import/run/fleet", response_class=PlainTextResponse)
def run_fleet():
    return PlainTextResponse("HTTP import je vypnutý. Použijte kontrolovaný lokální import po záloze.", status_code=410)

@app.get("/import/run/fuel", response_class=PlainTextResponse)
def run_fuel():
    return PlainTextResponse("HTTP import je vypnutý. Použijte kontrolovaný lokální import po záloze.", status_code=410)

# Keep the disabled literal import triggers ahead of /import/{batch_id}/fuel.
app.include_router(staging_router, dependencies=fleet_dependencies)
