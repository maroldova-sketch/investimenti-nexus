"""Real JWT/auth and synthetic SQLite integration tests of the fleet pilot.

No production database, user session, external service, message or payment.
"""
import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['SECRET_KEY'] = 'synthetic-fleet-command-test-key-never-use-in-production'
import json
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.core.models.base import Base, get_db
from backend.core.models.kernel import AuditLog, Entity, NexusRole, Person, RoleAssignment, ScopeType, UserAccount
from backend.core.security.auth import create_token
from backend.modules.fleet.models import FleetEvent, OdometerReading, Vehicle
from backend.modules.fleet.commands import FleetCommand, validate_schema


class FleetCommandTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        roles = [('owner', NexusRole.OWNER, ScopeType.ALL, None, None, None),
                 ('other-owner', NexusRole.OWNER, ScopeType.ALL, None, None, None),
                 ('admin', NexusRole.ADMIN, ScopeType.ALL, None, None, None),
                 ('fleet', NexusRole.FLEET_MANAGER, ScopeType.ALL, None, None, None),
                 ('scoped', NexusRole.FLEET_MANAGER, ScopeType.ENTITY, 'a', None, None),
                 ('division', NexusRole.FLEET_MANAGER, ScopeType.DIVISION, 'a', None, None),
                 ('expired', NexusRole.OWNER, ScopeType.ALL, None, None, '2000-01-01'),
                 ('future', NexusRole.OWNER, ScopeType.ALL, None, '2999-01-01', None),
                 ('invalid-date', NexusRole.OWNER, ScopeType.ALL, None, 'not-a-date', None),
                 ('generic-manager', NexusRole.MANAGER, ScopeType.ALL, None, None, None),
                 ('inconsistent', NexusRole.OWNER, ScopeType.ALL, 'a', None, None),
                 ('readonly', NexusRole.READONLY, ScopeType.ALL, None, None, None)]
        with self.Session.begin() as db:
            db.add(Entity(id='a', code='TEST', name='Test', legal_name='Test', division='clinic'))
            for name, *_ in roles:
                db.add(Person(id=name, first_name='Test', last_name=name))
            db.flush()
            for name, role, scope, entity, start, end in roles:
                db.add(UserAccount(id='acct-' + name, person_id=name, email=name + '@example.invalid', hashed_password='unused'))
                db.add(RoleAssignment(person_id=name, role=role, scope_type=scope, scope_entity_id=entity,
                                      valid_from=start, valid_to=end))
            db.add(Vehicle(id='v', spz='TEST-01', make='Test', model='Auto', entity_id='a', km_current=100))
        self.app = FastAPI()
        def db_session():
            with self.Session() as db:
                yield db
        self.app.dependency_overrides[get_db] = db_session
        from backend.modules.fleet.pilot import install
        with patch('backend.modules.fleet.pilot.engine', self.engine):
            install(self.app)
        self.client = TestClient(self.app, follow_redirects=False)
        self.tokens = {name: create_token({'sub': 'acct-' + name}) for name, *_ in roles}

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def headers(self, user='owner', csrf=False):
        headers = {'Authorization': 'Bearer ' + self.tokens[user]}
        if csrf:
            meta = self.client.get('/api/fleet/elias/meta', headers=headers)
            self.assertEqual(meta.status_code, 200, meta.text)
            headers['X-Fleet-CSRF'] = meta.json()['csrf']
        return headers

    def detail(self, user='owner'):
        response = self.client.get('/api/fleet/elias/vehicles/v', headers=self.headers(user))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def body(self, **changes):
        body = dict(vehicle_id='v', expected_revision=self.detail()['revision'],
                    idempotency_key=str(uuid4()), kind='odometer', effective_at='2020-03-10T12:00:00+01:00',
                    source='elias', km=200)
        body.update(changes)
        return body

    def post(self, body, user='owner', csrf=True, **headers):
        return self.client.post('/api/fleet/elias/commands', json=body,
                                headers={**self.headers(user, csrf), **headers})

    def counts(self):
        with self.Session() as db:
            return tuple(db.query(cls).count() for cls in (OdometerReading, FleetEvent, FleetCommand, AuditLog))

    def test_real_auth_no_token_forged_token_and_valid_holding_mandates(self):
        self.assertEqual(self.client.get('/api/fleet/elias/vehicles').status_code, 303)
        self.assertEqual(self.client.get('/api/fleet/elias/vehicles', headers={'Authorization': 'Bearer invalid'}).status_code, 303)
        for user in ('owner', 'admin', 'fleet'):
            self.assertEqual(self.client.get('/api/fleet/elias/vehicles', headers=self.headers(user)).status_code, 200)

    def test_scoped_expired_future_invalid_and_generic_roles_denied(self):
        for user in ('scoped', 'division', 'expired', 'future', 'invalid-date', 'generic-manager', 'inconsistent', 'readonly'):
            with self.subTest(user=user):
                self.assertEqual(self.client.get('/api/fleet/elias/vehicles/v', headers=self.headers(user)).status_code, 403)
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_revocation_checked_again_after_meta_and_on_readback(self):
        body = self.body()
        headers = self.headers(csrf=True)
        with self.Session.begin() as db:
            db.query(RoleAssignment).filter_by(person_id='owner').delete()
        response = self.client.post('/api/fleet/elias/commands', json=body, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_disabled_account_or_person_is_denied(self):
        with self.Session.begin() as db:
            db.get(UserAccount, 'acct-owner').is_active = False
        self.assertEqual(self.client.get('/api/fleet/elias/vehicles', headers=self.headers()).status_code, 303)
        with self.Session.begin() as db:
            db.get(UserAccount, 'acct-owner').is_active = True
            db.get(Person, 'owner').is_active = False
        self.assertEqual(self.client.get('/api/fleet/elias/vehicles', headers=self.headers()).status_code, 403)

    def test_csrf_missing_wrong_actor_and_cross_origin_are_denied(self):
        body = self.body()
        self.assertEqual(self.post(body, csrf=False).status_code, 403)
        self.assertEqual(self.post(body, csrf=False, **{'X-Fleet-CSRF': 'invalid'}).status_code, 403)
        foreign_token = self.headers('other-owner', csrf=True)['X-Fleet-CSRF']
        self.assertEqual(self.post(body, csrf=False, **{'X-Fleet-CSRF': foreign_token}).status_code, 403)
        self.assertEqual(self.post(body, Origin='https://different.example').status_code, 403)
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_record_audit_journal_committed_and_readback_matches_exact_id(self):
        body = self.body()
        response = self.post(body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(self.counts(), (1, 0, 1, 1))
        readback = self.client.get('/api/fleet/elias/commands/' + result['id'], headers=self.headers())
        self.assertEqual(readback.status_code, 200, readback.text)
        self.assertEqual(readback.json(), result)
        detail = self.detail()
        self.assertEqual(detail['km_current'], 200)
        self.assertEqual(detail['revision'], result['revision'])
        self.assertEqual(detail['odometer_readings'][0]['id'], result['record_id'])
        with self.Session() as db:
            audit = db.query(AuditLog).one()
            self.assertEqual(audit.resource_id, result['id'])
            self.assertEqual(audit.user_id, 'acct-owner')
            self.assertEqual(audit.entity_id, 'a')
            self.assertEqual(json.loads(audit.detail)['record_id'], result['record_id'])

    def test_exact_replay_returns_same_result_before_stale_revision_check(self):
        body = self.body()
        first = self.post(body)
        second = self.post(body)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(self.counts(), (1, 0, 1, 1))

    def test_key_reuse_with_changed_content_is_conflict(self):
        body = self.body()
        self.assertEqual(self.post(body).status_code, 200)
        response = self.post({**body, 'km': 201})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.counts(), (1, 0, 1, 1))

    def test_stale_revision_does_not_write_or_advance_vehicle_revision(self):
        body = self.body()
        self.assertEqual(self.post(body).status_code, 200)
        before = self.detail()['revision']
        response = self.post({**body, 'idempotency_key': str(uuid4()), 'effective_at': '2020-03-11T12:00:00+01:00', 'km': 201})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.detail()['revision'], before)
        self.assertEqual(self.counts(), (1, 0, 1, 1))

    def test_odometer_strict_types_range_timezone_future_and_extra_fields(self):
        for changes in ({'km': -1}, {'km': 10000000}, {'km': 1.5}, {'km': '200'}, {'km': True},
                        {'effective_at': '2020-03-10T12:00:00'}, {'effective_at': '2020-02-30T12:00:00+01:00'},
                        {'effective_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
                        {'actor_id': 'acct-other-owner'}, {'description': 'not an odometer field'}):
            with self.subTest(changes=changes):
                response = self.post(self.body(**changes))
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_effective_time_requires_explicit_timezone_text_not_epoch_coercion(self):
        for value in (1583841600, 1583841600.0, '1583841600'):
            response = self.post(self.body(effective_at=value))
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_chronology_checks_both_neighbors_and_preserves_latest_value(self):
        with self.Session.begin() as db:
            db.add_all([OdometerReading(vehicle_id='v', km=100, reading_date='2020-03-01'),
                        OdometerReading(vehicle_id='v', km=300, reading_date='2020-03-20')])
            db.get(Vehicle, 'v').km_current = 300
        for km in (99, 301):
            response = self.post(self.body(km=km))
            self.assertEqual(response.status_code, 409, response.text)
        response = self.post(self.body(km=200))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.detail()['km_current'], 300)
        self.assertEqual(self.counts(), (3, 0, 1, 1))

    def test_same_prague_day_and_malformed_legacy_history_are_conflicts(self):
        self.assertEqual(self.post(self.body()).status_code, 200)
        # 23:30 UTC on March 9 is March 10 in Prague.
        response = self.post(self.body(effective_at='2020-03-09T23:30:00Z'))
        self.assertEqual(response.status_code, 409)
        with self.Session.begin() as db:
            db.add(OdometerReading(vehicle_id='v', km=201, reading_date='not-a-date'))
        response = self.post(self.body(effective_at='2020-03-11T12:00:00+01:00'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.counts(), (2, 0, 1, 1))

    def test_legacy_current_value_cannot_be_overwritten_backwards(self):
        self.assertEqual(self.post(self.body(km=99)).status_code, 409)
        self.assertEqual(self.detail()['km_current'], 100)
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_defect_readback_does_not_change_odometer_and_is_actor_scoped(self):
        body = self.body(kind='defect', km=None, description='  Brzdy vydávají hluk.  ')
        response = self.post(body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(self.counts(), (0, 1, 1, 1))
        detail = self.detail()
        self.assertEqual(detail['km_current'], 100)
        self.assertEqual(detail['events'][0]['id'], result['record_id'])
        self.assertEqual(detail['events'][0]['description'], 'Závada: Brzdy vydávají hluk.')
        url = '/api/fleet/elias/commands/' + result['id']
        self.assertEqual(self.client.get(url, headers=self.headers()).json(), result)
        self.assertEqual(self.client.get(url, headers=self.headers('other-owner')).status_code, 404)
        with self.Session.begin() as db:
            db.query(FleetEvent).filter_by(id=result['record_id']).delete()
        self.assertEqual(self.client.get(url, headers=self.headers()).status_code, 409)

    def test_defect_requires_nonblank_description_and_rejects_odometer_field(self):
        for changes in ({'description': '  '}, {'description': None}, {'description': 'x' * 2001}, {'description': 'Defect', 'km': 201}):
            response = self.post(self.body(kind='defect', **{'km': None, **changes}))
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_failure_of_audit_or_journal_insert_rolls_back_everything(self):
        for target in ('audit_log', 'fleet_command'):
            before = self.detail()['revision']
            body = self.body()
            def fail_insert(connection, cursor, statement, params, context, many):
                if statement.lower().startswith('insert into ' + target):
                    raise OperationalError(statement, params, sqlite3.OperationalError('synthetic failure'))
            event.listen(self.engine, 'before_cursor_execute', fail_insert)
            try:
                response = self.post(body)
            finally:
                event.remove(self.engine, 'before_cursor_execute', fail_insert)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(self.counts(), (0, 0, 0, 0))
            self.assertEqual(self.detail()['revision'], before)
            self.assertEqual(self.detail()['km_current'], 100)

    def test_request_body_limit_blocks_before_mutation_and_no_store(self):
        headers = {**self.headers(csrf=True), 'Content-Type': 'application/json'}
        body = json.dumps(self.body()).encode() + b' ' * 16384
        response = self.client.post('/api/fleet/elias/commands', content=body, headers=headers)
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(self.counts(), (0, 0, 0, 0))
        self.assertIn('no-store', self.client.get('/api/fleet/elias/vehicles', headers=self.headers()).headers.get('cache-control', ''))

    def test_latest_reading_cannot_erase_a_higher_legacy_current_value(self):
        with self.Session.begin() as db:
            db.add(OdometerReading(vehicle_id='v', km=100, reading_date='2020-03-01'))
            db.get(Vehicle, 'v').km_current = 500
        response = self.post(self.body(km=200))
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.detail()['km_current'], 500)
        self.assertEqual(self.counts(), (1, 0, 0, 0))

    def test_tampered_odometer_or_event_readback_is_not_reported_as_verified(self):
        response = self.post(self.body())
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        url = '/api/fleet/elias/commands/' + result['id']
        with self.Session.begin() as db:
            db.get(OdometerReading, result['record_id']).km = 999
        self.assertEqual(self.client.get(url, headers=self.headers()).status_code, 409)
        response = self.post(self.body(kind='defect', km=None, description='Původní závada'))
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        with self.Session.begin() as db:
            db.get(FleetEvent, result['record_id']).description = 'Změněný obsah'
        self.assertEqual(self.client.get('/api/fleet/elias/commands/' + result['id'], headers=self.headers()).status_code, 409)

    def test_unknown_legacy_role_does_not_grant_access_or_crash_auth(self):
        with self.Session.begin() as db:
            db.execute(text("UPDATE role_assignment SET role='FUTURE_UNKNOWN_ROLE' WHERE person_id='readonly'"))
        self.assertEqual(self.client.get('/api/fleet/elias/vehicles', headers=self.headers('readonly')).status_code, 403)

    def test_readback_rechecks_revocation_even_after_successful_record(self):
        response = self.post(self.body())
        self.assertEqual(response.status_code, 200, response.text)
        with self.Session.begin() as db:
            db.query(RoleAssignment).filter_by(person_id='owner').delete()
        self.assertEqual(self.client.get('/api/fleet/elias/commands/' + response.json()['id'], headers=self.headers()).status_code, 403)

    def test_exactly_16384_byte_body_is_accepted(self):
        body = json.dumps(self.body()).encode()
        body += b' ' * (16384 - len(body))
        response = self.client.post('/api/fleet/elias/commands', content=body,
                                   headers={**self.headers(csrf=True), 'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.counts(), (1, 0, 1, 1))

    def test_install_refuses_missing_schema_without_routes_or_tables(self):
        from backend.modules.fleet.pilot import install
        empty = create_engine('sqlite://')
        app = FastAPI()
        routes_before = list(app.routes)
        try:
            with patch('backend.modules.fleet.pilot.engine', empty):
                with self.assertRaises(RuntimeError):
                    install(app)
            self.assertEqual(inspect(empty).get_table_names(), [])
            self.assertEqual(app.routes, routes_before)
            self.assertFalse(getattr(app.state, 'fleet_pilot_enabled', False))
        finally:
            empty.dispose()

    def test_missing_schema_validation_is_read_only(self):
        empty = create_engine('sqlite://')
        before = inspect(empty).get_table_names()
        try:
            with self.assertRaises(RuntimeError):
                validate_schema(empty)
            self.assertEqual(inspect(empty).get_table_names(), before)
        finally:
            empty.dispose()


if __name__ == '__main__':
    unittest.main()
