"""Shared non-mutating startup gates for internal HR and the employee service."""
from pathlib import Path
from sqlalchemy import inspect
from sqlalchemy.engine import make_url


def validate_signing_key(secret_key):
    if len(secret_key) < 32 or secret_key == 'dev-secret-key-change-in-production':
        raise RuntimeError('HR requires a configured non-default signing key of at least 32 characters.')


def validate_schema(engine):
    from .models import HR_TABLES
    from backend.core.models.kernel import Person, Entity, RoleAssignment
    from backend.modules.people.models import Employment
    inspector = inspect(engine)
    for table in [Person.__table__, Entity.__table__, Employment.__table__, RoleAssignment.__table__, *HR_TABLES]:
        if not inspector.has_table(table.name):
            raise RuntimeError('Install the reviewed HR schema before enabling NEXUS_HR_ENABLED.')
        actual = {c['name'] for c in inspector.get_columns(table.name)}
        if not set(table.columns.keys()).issubset(actual):
            raise RuntimeError('The HR schema is incompatible. Review the migration before enabling it.')


def validate_database_location(database_url):
    # The existing Nexus engine is SQLite-specific. Do not imply support for a
    # new database driver or accidentally create a database in the current cwd.
    try:
        url = make_url(database_url)
        path = Path(url.database or '')
        if (url.drivername != 'sqlite' or not path.is_absolute() or not path.is_file()
                or path.is_symlink() or url.query):
            raise ValueError
    except Exception:
        raise RuntimeError('Employee entry requires an explicit absolute path to the existing Nexus SQLite database.') from None


def validate_entry_configuration(settings):
    from . import runtime
    validate_signing_key(settings.secret_key)
    validate_database_location(settings.database_url)
    if not runtime.invitations_ready():
        raise RuntimeError('Configure the HTTPS employee origin and TLS code-delivery adapter before starting entry.')
    if not runtime.uploads_ready():
        raise RuntimeError('Configure the private document directory, encryption keyring and ClamAV socket before starting entry.')
