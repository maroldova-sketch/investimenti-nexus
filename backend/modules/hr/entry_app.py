"""Isolated ASGI composition: expose employee routes, never the main Nexus app.

Run behind the reviewed HTTPS proxy using uvicorn's --factory flag. This shares
the existing database and domain operations; it does not copy employee records.
"""
import os
from pathlib import Path
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse

PUBLIC_PATHS = frozenset({
    '/hr/entry', '/hr/api/code', '/hr/api/verify', '/hr/api/meta', '/hr/api/logout',
    '/hr/api/cases/{case_id}', '/hr/api/cases/{case_id}/draft', '/hr/api/cases/{case_id}/actions',
    '/hr/api/cases/{case_id}/documents', '/hr/api/cases/{case_id}/documents/{document_id}',
    '/hr/api/cases/{case_id}/documents/{document_id}/withdraw',
})


def create_app():
    # Gate configuration before importing the routes/engine; factory construction
    # performs no schema creation, recipient creation or outgoing mail.
    if os.environ.get('NEXUS_HR_ENABLED') != '1':
        raise RuntimeError('Enable NEXUS_HR_ENABLED explicitly before starting employee entry.')
    from backend.config import get_settings
    from .startup import validate_entry_configuration, validate_schema
    settings = get_settings()
    validate_entry_configuration(settings)
    from backend.core.models.base import engine
    from .portal import router
    from .boundary import HRBoundary
    validate_schema(engine)
    app = FastAPI(title='NEXUS employee entry', docs_url=None, redoc_url=None,
                  openapi_url=None, redirect_slashes=False)
    routes = [route for route in router.routes if route.path in PUBLIC_PATHS]
    if {route.path for route in routes} != PUBLIC_PATHS:
        raise RuntimeError('Employee route composition is incomplete; review the release.')
    # Include via FastAPI so route dependency providers belong to this app;
    # never share mutable APIRoute objects with the internal application.
    app.include_router(APIRouter(routes=routes))
    app.add_middleware(HRBoundary)
    static = Path(__file__).resolve().parents[3] / 'frontend/static/hr'

    @app.get('/static/hr/{asset}', include_in_schema=False)
    def employee_asset(asset: str):
        if asset not in {'app.js', 'style.css'}:
            raise HTTPException(404)
        return FileResponse(static / asset, headers={'X-Content-Type-Options': 'nosniff',
                                                     'Cache-Control': 'no-cache'})

    app.state.hr_enabled = True
    return app
