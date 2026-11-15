"""Explicit additive migration. Never runs on import or application startup."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, inspect
from backend.modules.people.models import Employment  # register parent metadata
from backend.modules.hr.models import HR_TABLES
from backend.core.models.base import Base


def main():
    parser = argparse.ArgumentParser(description='Install only the additive HR tables into an explicitly selected Nexus database.')
    parser.add_argument('--database-url', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    engine = create_engine(args.database_url)
    existing = set(inspect(engine).get_table_names())
    if not {'person', 'entity', 'employment'}.issubset(existing):
        raise SystemExit('Target does not contain the required Nexus parent tables.')
    missing = [t.name for t in HR_TABLES if t.name not in existing]
    print('New tables:', ', '.join(missing) or 'none')
    if args.apply:
        Base.metadata.create_all(engine, tables=HR_TABLES)
        print('HR tables installed. Existing tables were not modified.')
    else:
        print('Dry run. Add --apply after backup and review.')


if __name__ == '__main__':
    main()
