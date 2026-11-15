"""Versioned HR case intake; enabled explicitly after schema installation."""


def install(app):
    from sqlalchemy import inspect
    from backend.config import get_settings
    from backend.core.models.base import engine
    from .models import HR_TABLES
    from .routes import router
    from .portal import router as portal_router
    from .boundary import HRBoundary
    settings = get_settings()
    if len(settings.secret_key) < 32 or settings.secret_key == 'dev-secret-key-change-in-production':
        raise RuntimeError('HR requires a configured non-default signing key of at least 32 characters.')
    inspector = inspect(engine)
    for table in HR_TABLES:
        if not inspector.has_table(table.name):
            raise RuntimeError('Install the reviewed HR schema before enabling NEXUS_HR_ENABLED.')
        actual = {c['name'] for c in inspector.get_columns(table.name)}
        if not set(table.columns.keys()).issubset(actual):
            raise RuntimeError('The HR schema is incompatible. Review the migration before enabling it.')
    app.include_router(router)
    app.include_router(portal_router)
    app.add_middleware(HRBoundary)
    app.state.hr_enabled = True
