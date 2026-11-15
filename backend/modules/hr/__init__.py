"""Versioned HR case intake; enabled explicitly after schema installation."""


def install(app):
    from backend.config import get_settings
    from backend.core.models.base import engine
    from .startup import validate_schema, validate_signing_key
    from .routes import router
    from .portal import router as portal_router
    from .boundary import HRBoundary
    settings = get_settings()
    validate_signing_key(settings.secret_key)
    validate_schema(engine)
    app.include_router(router)
    app.include_router(portal_router)
    app.add_middleware(HRBoundary)
    app.state.hr_enabled = True
