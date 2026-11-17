"""Versioned HR case intake; enabled explicitly after schema installation."""


def install(app):
    from backend.config import get_settings
    from backend.core.models.base import engine
    from .startup import validate_schema, hr_signing_key
    from .routes import router
    from .portal import router as portal_router
    from .boundary import HRBoundary
    settings = get_settings()
    hr_signing_key(settings)
    validate_schema(engine)
    from .wizard import router as wizard_router
    from .terms import router as terms_router
    from .export import router as export_router
    app.include_router(router)
    app.include_router(portal_router)
    app.include_router(wizard_router)
    app.include_router(terms_router)
    app.include_router(export_router)
    app.add_middleware(HRBoundary)
    app.state.hr_enabled = True
