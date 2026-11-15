"""Synthetic data only. Never opens the checked-in or configured Nexus DB."""
import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['SECRET_KEY'] = 'synthetic-unit-test-key-never-use-in-production'
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.core.models.base import Base, get_db
from backend.core.models.kernel import Person, Entity, RoleAssignment, NexusRole, ScopeType
from backend.core.security.auth import get_current_user
from backend.modules.people.models import Employment
from backend.modules.hr.models import HRCase, HRSubmission
from backend.modules.hr.routes import router, commit
from backend.modules.hr.schema import normalize


COMPLETE = dict(first_name='Test', last_name='Osoba', birth_date='1990-01-01',
                citizenship='CZ', address_permanent='Testovací 1', personal_id_status='not_assigned',
                health_insurance='111', tax_residency='CZ', declaration='no')


class HRCaseTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session.begin() as db:
            for p in ['employee-a', 'employee-b', 'hr-a', 'hr-b', 'finance-a', 'expired', 'division', 'readonly', 'owner']:
                db.add(Person(id=p, first_name='Testovací', last_name=p))
            db.add_all([Entity(id='a', code='TEST_A', name='Testovací firma A', legal_name='Test A s.r.o.', ico='00000001', division='clinic'),
                        Entity(id='b', code='TEST_B', name='Testovací firma B', legal_name='Test B s.r.o.', ico='00000002', division='industry')])
            db.flush()
            db.add_all([Employment(id='work-a', person_id='employee-a', entity_id='a', position='Koordinátor', date_start='2026-01-01'),
                        Employment(id='work-b', person_id='employee-b', entity_id='b', position='Specialista', date_start='2026-01-01'),
                        Employment(id='work-a2', person_id='employee-a', entity_id='b', employment_type='DPP', date_start='2026-01-01')])
            for person, role, scope, entity in [('hr-a', NexusRole.HR, ScopeType.ENTITY, 'a'), ('hr-b', NexusRole.HR, ScopeType.ENTITY, 'b'),
                                                ('finance-a', NexusRole.FINANCE, ScopeType.ENTITY, 'a'), ('expired', NexusRole.HR, ScopeType.ENTITY, 'a'),
                                                ('division', NexusRole.HR, ScopeType.DIVISION, 'a'), ('owner', NexusRole.OWNER, ScopeType.ALL, None)]:
                db.add(RoleAssignment(person_id=person, role=role, scope_type=scope, scope_entity_id=entity,
                                      valid_to='2000-01-01' if person == 'expired' else None))
        app = FastAPI()
        app.include_router(router)
        def db_session():
            with self.Session() as db:
                yield db
        def user(request: Request):
            name = request.headers.get('Authorization', '').removeprefix('Bearer ')
            if not name:
                raise HTTPException(401)
            return SimpleNamespace(id=name, person_id=name, roles=[])
        app.dependency_overrides[get_db] = db_session
        app.dependency_overrides[get_current_user] = user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def call(self, method, path, body=None, user='hr-a', csrf=True):
        headers = {'Authorization': 'Bearer ' + user}
        if method != 'GET' and csrf:
            headers['X-HR-CSRF'] = self.client.get('/api/hr/meta', headers=headers).json()['csrf']
        return self.client.request(method, '/api/hr' + path, json=body, headers=headers)

    def create(self, employment='work-a', user='hr-a', request_key=None):
        response = self.call('POST', '/cases', dict(employment_id=employment, request_key=request_key or str(uuid4())), user)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def save(self, case, answers=None, user='employee-a'):
        r = self.call('PUT', f"/cases/{case['id']}/draft", dict(expected_version=case['version'], answers=answers or COMPLETE), user)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def transition(self, case, action, user='hr-a', **extra):
        body = dict(expected_version=case['version'], revision=case['revision'], request_key=str(uuid4()), action=action, **extra)
        return self.call('POST', f"/cases/{case['id']}/actions", body, user)

    def submitted(self):
        c = self.save(self.create())
        r = self.transition(c, 'submit', 'employee-a')
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def configure(self, case, blocks=False, status='pending', evidence='', reason=''):
        return self.call('PUT', f"/cases/{case['id']}/requirements", dict(expected_version=case['version'], confirmed=True,
                         items=[dict(id='payroll', label='Mzdové podklady', blocks_payroll=blocks, status=status, evidence_ref=evidence, reason=reason)]))

    def reviewed(self):
        c = self.submitted()
        c = self.configure(c, True, 'verified', 'protected-document-reference').json()
        r = self.transition(c, 'review', confirmed=True)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_login_and_csrf_required(self):
        self.assertEqual(self.client.get('/api/hr/cases').status_code, 401)
        self.assertEqual(self.call('POST', '/cases', {}, csrf=False).status_code, 422)
        c = self.create()
        self.assertEqual(self.call('PUT', f"/cases/{c['id']}/draft", dict(expected_version=c['version'], answers={}), csrf=False).status_code, 403)

    def test_origin_is_checked(self):
        token = self.call('GET', '/meta').json()['csrf']
        r = self.client.post('/api/hr/cases', json=dict(employment_id='work-a', request_key=str(uuid4())),
                             headers={'Authorization':'Bearer hr-a', 'X-HR-CSRF':token, 'Origin':'https://unrelated.example'})
        self.assertEqual(r.status_code, 403)

    def test_cross_company_and_expired_roles_denied(self):
        c = self.create()
        for user in ['hr-b', 'expired', 'readonly', 'employee-b']:
            self.assertEqual(self.call('GET', f"/cases/{c['id']}", user=user).status_code, 404)
            self.assertEqual(self.call('GET', '/cases', user=user).json(), [])
        self.assertEqual(self.call('GET', f"/cases/{c['id']}", user='division').status_code, 200)

    def test_concurrent_employments_keep_context_separate(self):
        a = self.create()
        b = self.create('work-a2', 'hr-b')
        self.assertNotEqual(a['id'], b['id'])
        self.assertEqual(len(self.call('GET', '/cases', user='employee-a').json()), 2)
        self.assertEqual(len(self.call('GET', '/cases', user='hr-a').json()), 1)

    def test_create_idempotent_and_no_duplicate_open_case(self):
        request_key = str(uuid4())
        c = self.create(request_key=request_key)
        self.assertEqual(self.create(request_key=request_key)['id'], c['id'])
        r = self.call('POST', '/cases', dict(employment_id='work-a', request_key=str(uuid4())))
        self.assertEqual(r.status_code, 409)

    def test_draft_survives_new_request_and_rejects_stale_writer(self):
        c = self.create()
        updated = self.save(c)
        restored = self.call('GET', f"/cases/{c['id']}", user='employee-a').json()
        self.assertEqual(restored['answers']['first_name'], 'Test')
        self.assertGreater(updated['version'], c['version'])
        r = self.call('PUT', f"/cases/{c['id']}/draft", dict(expected_version=c['version'], answers={'first_name':'Stale'}))
        self.assertEqual(r.status_code, 409)

    def test_database_version_rejects_concurrent_transactions(self):
        c = self.create()
        with self.Session() as one, self.Session() as two:
            a, b = one.get(HRCase,c['id']), two.get(HRCase,c['id'])
            a.draft = {'first_name':'One'}
            commit(one)
            b.draft = {'first_name':'Two'}
            with self.assertRaises(HTTPException) as cm:
                commit(two)
            self.assertEqual(cm.exception.status_code, 409)

    def test_hidden_family_data_removed_and_unknown_fields_rejected(self):
        c = self.create()
        answers = {**COMPLETE, 'children_claim':'yes', 'second_taxpayer':'Hidden', 'children':[{'name':'Hidden child'}]}
        saved = self.save(c, answers)
        self.assertNotIn('children', saved['answers'])
        self.assertNotIn('second_taxpayer', saved['answers'])
        with self.assertRaises(ValueError):
            normalize({'salary':'99999'})

    def test_child_months_and_conditional_required_fields(self):
        c = self.create()
        a = {**COMPLETE,'declaration':'yes','tax_residency':'CZ','children_claim':'yes',
             'children':[{'name':'Test child','months':[13]}]}
        r = self.call('PUT',f"/cases/{c['id']}/draft",dict(expected_version=c['version'],answers=a),'employee-a')
        self.assertEqual(r.status_code,422)
        c = self.save(c, {**COMPLETE,'declaration':'yes'})
        self.assertEqual(self.transition(c,'submit','employee-a').status_code,422)

    def test_submit_is_immutable_and_replay_is_idempotent(self):
        c = self.save(self.create())
        body = dict(expected_version=c['version'],revision=0,request_key=str(uuid4()),action='submit')
        r = self.call('POST', f"/cases/{c['id']}/actions", body, 'employee-a')
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.call('POST', f"/cases/{c['id']}/actions", body, 'employee-a').json()['revision'],1)
        c = r.json()
        self.assertEqual(self.call('PUT',f"/cases/{c['id']}/draft",dict(expected_version=c['version'],answers=COMPLETE),'employee-a').status_code,409)
        body['revision']=1
        self.assertEqual(self.call('POST',f"/cases/{c['id']}/actions",body,'employee-a').status_code,409)
        with self.Session() as db:
            self.assertEqual(db.query(HRSubmission).count(),1)

    def test_return_and_resubmit_preserves_old_snapshot(self):
        c = self.submitted()
        first = self.call('GET',f"/cases/{c['id']}/submissions/1").json()
        c = self.transition(c,'return',note='Prosím upřesnit adresu.').json()
        c = self.save(c,{**COMPLETE,'address_permanent':'Testovací 2'})
        c = self.transition(c,'submit','employee-a').json()
        self.assertEqual(c['revision'],2)
        self.assertEqual(self.call('GET',f"/cases/{c['id']}/submissions/1").json(),first)

    def test_finance_cannot_rewrite_answers_and_employee_cannot_review(self):
        c = self.submitted()
        self.assertEqual(self.transition(c,'review','employee-a',confirmed=True).status_code,403)
        self.assertEqual(self.call('PUT',f"/cases/{c['id']}/draft",dict(expected_version=c['version'],answers=COMPLETE),'finance-a').status_code,403)

    def test_requirements_need_evidence_and_block_review(self):
        c = self.submitted()
        self.assertEqual(self.transition(c,'review',confirmed=True).status_code,409)
        self.assertEqual(self.configure(c,True,'verified').status_code,422)
        self.assertEqual(self.configure(c,False,'deferred').status_code,422)
        c = self.configure(c,True,'pending').json()
        self.assertEqual(self.transition(c,'review',confirmed=True).status_code,409)

    def test_payroll_accepts_exact_revision_and_closes_case(self):
        c = self.reviewed()
        bad = dict(expected_version=c['version'],revision=0,request_key=str(uuid4()),action='payroll_receive',confirmed=True)
        self.assertEqual(self.call('POST',f"/cases/{c['id']}/actions",bad,'finance-a').status_code,409)
        self.assertEqual(self.transition(c,'payroll_receive','hr-a',confirmed=True).status_code,403)
        c = self.transition(c,'payroll_receive','finance-a',confirmed=True).json()
        self.assertEqual(c['status'],'payroll_received')
        self.assertEqual(self.transition(c,'return',note='Late change').status_code,409)
        new = self.create()
        self.assertNotEqual(c['id'],new['id'])

    def test_employee_cannot_self_approve_with_owner_role(self):
        c = self.submitted()
        with self.Session.begin() as db:
            db.add(RoleAssignment(person_id='employee-a',role=NexusRole.OWNER,scope_type=ScopeType.ALL))
        self.assertEqual(self.transition(c,'review','employee-a',confirmed=True).status_code,403)

    def test_context_retarget_requires_hr_review(self):
        c = self.create()
        with self.Session.begin() as db:
            db.get(Employment,'work-a').entity_id='b'
        self.assertEqual(self.call('GET',f"/cases/{c['id']}").status_code,409)

    def test_api_responses_are_not_cacheable(self):
        self.assertEqual(self.call('GET','/meta').headers.get('cache-control'),'no-store')

    def test_install_refuses_default_signing_key(self):
        from backend.modules.hr import install
        with patch('backend.config.get_settings', return_value=SimpleNamespace(secret_key='dev-secret-key-change-in-production')):
            with self.assertRaisesRegex(RuntimeError, 'signing key'):
                install(FastAPI())

    def test_install_refuses_missing_schema(self):
        from backend.modules.hr import install
        empty = create_engine('sqlite://')
        try:
            with patch('backend.core.models.base.engine', empty):
                with self.assertRaisesRegex(RuntimeError, 'schema'):
                    install(FastAPI())
        finally:
            empty.dispose()

    def test_install_registers_feature_after_schema_check(self):
        from backend.modules.hr import install
        app = FastAPI()
        with patch('backend.core.models.base.engine', self.engine):
            install(app)
        self.assertTrue(app.state.hr_enabled)
        self.assertIn('/people/hr', [r.path for r in app.routes])


if __name__ == '__main__':
    unittest.main()
