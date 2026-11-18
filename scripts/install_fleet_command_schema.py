"""Add only the fleet command journal to an explicitly selected existing DB."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from backend.modules.fleet.commands import FLEET_COMMAND_TABLES, validate_schema
from backend.core.models.base import Base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-url', required=True)
    parser.add_argument('--apply', action='store_true', help='Apply after a verified database backup')
    args = parser.parse_args()
    url = make_url(args.database_url)
    if url.get_backend_name() == 'sqlite':
        path = Path(url.database or '')
        if not path.is_absolute() or not path.is_file() or url.query:
            raise SystemExit('SQLite migration requires an existing absolute database file and no URI query.')
        # mode=rw prevents creating a new database even if the file disappears.
        url = url.set(database=path.as_uri(), query={'mode': 'rw', 'uri': 'true'})
    engine = create_engine(url)
    try:
        existing = set(inspect(engine).get_table_names())
        parents = {'vehicle', 'vehicle_assignment', 'odometer_reading', 'fleet_event', 'audit_log',
                   'person', 'user_account', 'role_assignment'}
        if not parents.issubset(existing):
            raise SystemExit('Required existing fleet tables are missing; no schema installed.')
        missing = sorted({t.name for t in FLEET_COMMAND_TABLES} - existing)
        print('Missing additive tables:', ', '.join(missing) or 'none')
        if args.apply:
            Base.metadata.create_all(engine, tables=FLEET_COMMAND_TABLES)
            validate_schema(engine)
            print('Fleet command schema verified. Feature remains controlled by NEXUS_FLEET_ELIAS_ENABLED.')
        elif not missing:
            validate_schema(engine)
        else:
            print('Dry run only. Back up the canonical database before --apply.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
