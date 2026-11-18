"""Explicitly enabled, holding-manager-only fleet pilot."""
from fastapi import Depends
from backend.config import get_settings
from backend.core.models.base import engine
from .commands import legacy_readonly, router, validate_schema
from .command_boundary import FleetBoundary


def install(app):
    secret = get_settings().secret_key
    if len(secret) < 32 or secret == 'dev-secret-key-change-in-production' or secret.lower().startswith(('change', 'default', 'secret')):
        raise RuntimeError('Fleet pilot requires the existing configured strong session secret.')
    validate_schema(engine)
    app.include_router(router)
    app.add_middleware(FleetBoundary)
    app.state.fleet_pilot_enabled = True
    return [Depends(legacy_readonly)]
