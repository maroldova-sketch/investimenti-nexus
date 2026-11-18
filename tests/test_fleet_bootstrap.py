"""Check actual application route order and disabled legacy import entrypoints."""
import os
import subprocess
import sys
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FleetBootstrapTests(unittest.TestCase):
    def run_script(self, script, enabled='0'):
        env = dict(os.environ, DATABASE_URL='sqlite://', NEXUS_HR_ENABLED='0',
                   NEXUS_FLEET_ELIAS_ENABLED=enabled, SECRET_KEY='synthetic-bootstrap-key-never-use-in-production')
        return subprocess.run([sys.executable, '-c', script], cwd=ROOT, env=env, capture_output=True, text=True)

    def test_import_triggers_are_inert_and_literal_paths_win(self):
        result = self.run_script('''
from fastapi.testclient import TestClient
from starlette.routing import Match
from main import app
c = TestClient(app)
for path in ['/import/run/fleet', '/import/run/fuel']:
    assert c.get(path).status_code == 410, path
for path, expected in [('/fleet/phm', 'phm_overview'), ('/fleet/trips', 'trips_board')]:
    scope = {'type':'http', 'path':path, 'method':'GET', 'root_path':''}
    match = next(r for r in app.routes if r.matches(scope)[0] == Match.FULL)
    assert '{vehicle_id}' not in match.path, (path, match.path)
assert app.state.fleet_pilot_enabled is False
assert not any(getattr(r, 'path', '') == '/api/fleet/elias/commands' for r in app.routes)
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_enabled_pilot_fails_closed_without_schema(self):
        result = self.run_script('import main', enabled='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Fleet schema is not installed', result.stderr)

    def test_migration_never_creates_missing_database_even_on_apply(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'missing.db'
            for flags in ([], ['--apply']):
                result = subprocess.run([sys.executable, 'scripts/install_fleet_command_schema.py',
                                         '--database-url', 'sqlite:///' + str(path), *flags],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(path.exists())

    def test_migration_dry_run_then_only_additive_apply(self):
        from sqlalchemy import create_engine, inspect
        from backend.modules.fleet.commands import FleetCommand
        from backend.core.models.base import Base
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'existing.db'
            engine = create_engine('sqlite:///' + str(path))
            Base.metadata.create_all(engine, tables=[t for t in Base.metadata.sorted_tables if t.name != 'fleet_command'])
            before = set(inspect(engine).get_table_names())
            for flags in ([], ['--apply'], ['--apply']):
                result = subprocess.run([sys.executable, 'scripts/install_fleet_command_schema.py',
                                         '--database-url', 'sqlite:///' + str(path), *flags],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = before | {'fleet_command'} if flags else before
                self.assertEqual(set(inspect(engine).get_table_names()), expected)
            engine.dispose()


if __name__ == '__main__':
    unittest.main()
