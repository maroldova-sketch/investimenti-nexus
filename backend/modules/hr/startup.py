"""Shared non-mutating startup gates for internal HR and the employee service."""
import os
from pathlib import Path
from sqlalchemy import inspect
from sqlalchemy.engine import make_url


def validate_signing_key(secret_key, nexus_key=None):
    if (len(secret_key) < 32 or secret_key == 'dev-secret-key-change-in-production'
            or (nexus_key and secret_key == nexus_key)):
        raise RuntimeError('HR requires its own configured signing key (NEXUS_HR_SIGNING_KEY) of at least '
                           '32 characters, separate from the Nexus login key.')


def hr_signing_key(settings):
    """HR HMACs (CSRF, entry codes) use a dedicated key; the Nexus JWT key is untouched."""
    key = os.environ.get('NEXUS_HR_SIGNING_KEY', '')
    validate_signing_key(key, getattr(settings, 'secret_key', None))
    return key


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
    hr_signing_key(settings)
    validate_database_location(settings.database_url)
    if not runtime.invitations_ready():
        raise RuntimeError('Configure the HTTPS employee origin and TLS code-delivery adapter before starting entry.')
    if not runtime.uploads_ready():
        raise RuntimeError('Configure the private document directory, encryption keyring and ClamAV socket before starting entry.')
