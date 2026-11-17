"""Template v2, internal wizard, HR terms, payroll ownership and export. Synthetic data only."""
import io
import json
import zipfile
from datetime import date, timedelta
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
import test_hr_cases as fixtures
from test_hr_cases import COMPLETE
from backend.core.models.kernel import Person, RoleAssignment, NexusRole, ScopeType, AuditLog
from backend.modules.people.models import Employment
from backend.modules.hr.models import HRCase, HRSubmission
from backend.modules.hr.schema import V1, VERSION, normalize
from backend.modules.hr.schema_v2 import valid_rc, valid_account, AnswerError
from backend.modules.hr.wizard import router as wizard_router, valid_ico
from backend.modules.hr.terms import router as terms_router
from backend.modules.hr.export import router as export_router
from backend.modules.hr.guard import EntryGuard

CHILD = dict(name='Syntetické dítě', birth_date='2016-03-03', personal_id_status='assigned', personal_id='736028/5163',
             relationship='own', household='yes', order='1', months=[1, 2, 3], ztpp='no', study='')
TERMS = dict(expected_revision=0, effective_from='2026-11-01', source='Synthetic contract fixture',
             data=dict(workplace='Testovací provozovna', fte='1.0', weekly_hours='40', schedule='fixed',
                       pay_type='monthly', pay_amount='35000', equipment=[dict(item='Telefon', handed_over_on='2026-11-01')],
                       benefits=[dict(benefit='Stravenky', since='2026-11-01')],
                       car=dict(assigned='yes', vehicle='Testovací vůz', private_use='no')))


class Fixture(fixtures.unittest.TestCase):
    """Reuse the synthetic fixture helpers without re-running the v1-era tests."""
    locals().update({name: getattr(fixtures.HRCaseTests, name) for name in
                     ['setUp', 'tearDown', 'call', 'create', 'save', 'transition', 'submitted', 'configure', 'reviewed']})


class HRTemplateV2Tests(Fixture):
    def setUp(self):
        Fixture.setUp(self)
        for router in [wizard_router, terms_router, export_router]:
            self.client.app.include_router(router)

    # --- scenario helpers -------------------------------------------------
    def complete_case(self, employment='work-a', answers=None, hr='hr-a', employee='employee-a'):
        c = self.save(self.create(employment, hr), answers or COMPLETE, employee)
        r = self.transition(c, 'submit', employee)
        self.assertEqual(r.status_code, 200, r.text)
        c = r.json()
        c = self.configure(c, False, 'verified', 'inspection:2026-11-17').json()
        r = self.transition(c, 'review', hr, confirmed=True)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    # --- field validation ---------------------------------------------------
    def test_identifier_validators(self):
        self.assertTrue(valid_rc('736028/5163'))
        self.assertFalse(valid_rc('736028/5164'))
        self.assertTrue(valid_account('19-2000145399/0800'))
        self.assertTrue(valid_account('CZ65 0800 0000 1920 0014 5399'))
        self.assertFalse(valid_account('19-2000145398/0800'))
        self.assertTrue(valid_ico('26690756'))
        self.assertFalse(valid_ico('26690757'))

    def test_children_and_no_children_paths(self):
        without = normalize(COMPLETE, complete=True)
        self.assertNotIn('children', without)
        with_children = {**COMPLETE, 'declaration': 'yes', 'tax_period': '2026-11', 'ztpp_holder': 'no',
                         'children_claim': 'yes', 'children': [CHILD], 'second_taxpayer': 'claims',
                         'second_taxpayer_name': 'Druhý Poplatník'}
        out = normalize(with_children, complete=True)
        self.assertEqual(out['children'][0]['personal_id'], '736028/5163')  # identifiers stay text
        bad_child = {**with_children, 'children': [{**CHILD, 'personal_id': '736028/5164'}]}
        with self.assertRaises(AnswerError):
            normalize(bad_child, complete=True)
        no_months = {**with_children, 'children': [{**CHILD, 'months': []}]}
        with self.assertRaises(AnswerError):
            normalize(no_months, complete=True)

    def test_concurrent_employment_pension_and_deductions_branches(self):
        answers = {**COMPLETE, 'other_employment': 'yes', 'declaration_elsewhere_status': 'signed_elsewhere',
                   'declaration_elsewhere_period': 'od 2026-01 u Jiná firma s.r.o.',
                   'other_jobs': [dict(employer='Jiná firma s.r.o.', kind='DPP', date_from='2026-01-01', date_to='',
                                       insured='no', note='')],
                   'pension_status': 'old_age', 'pension_from': '2024-02-01',
                   'enforcement': 'yes', 'enforcement_detail': 'Exekutorský úřad, č. j. 123 EX 1/26',
                   'insolvency': 'no', 'voluntary_deductions': 'yes', 'voluntary_detail': 'Penzijní spoření'}
        out = normalize(answers, complete=True)
        self.assertEqual(out['other_jobs'][0]['kind'], 'DPP')
        from backend.modules.hr.schema_v2 import review_issues, suggested_requirements
        issues = ' '.join(review_issues(out))
        self.assertIn('Souběh zaměstnání', issues)
        self.assertIn('Důchod', issues)
        self.assertIn('Srážky', issues)
        ids = {r[0] for r in suggested_requirements(out)}
        self.assertTrue({'pension', 'deductions'} <= ids)
        missing_jobs = {**answers, 'other_jobs': []}
        with self.assertRaises(AnswerError):
            normalize(missing_jobs, complete=True)

    def test_foreigner_without_birth_number_and_permit_validity(self):
        soon = (date.today() + timedelta(days=20)).isoformat()
        answers = {**COMPLETE, 'citizenship': 'ukrajinská', 'citizenship_group': 'third', 'personal_id_status': 'not_assigned',
                   'sex': 'F', 'health_insured_number': '1234567890', 'cssz_number': '9876543210',
                   'foreign_social_security': 'no', 'id_doc_type': 'passport', 'id_doc_number': 'FX123456',
                   'id_doc_valid_to': '2030-01-01', 'residence_permit': 'temporary_protection',
                   'residence_permit_number': 'DO1234567', 'residence_valid_to': soon, 'free_access': 'yes'}
        out = normalize(answers, complete=True)
        self.assertNotIn('personal_id', out)
        from backend.modules.hr.schema_v2 import review_issues
        self.assertTrue(any('Pobyt platí do' in i for i in review_issues(out)))
        with self.assertRaises(AnswerError):
            normalize({**answers, 'id_doc_number': ''}, complete=True)

    def test_review_flag_is_unresolved_not_no_or_verified(self):
        answers = {**COMPLETE, 'birth_place': '', '_review': ['birth_place'], 'state_insured': 'review'}
        out = normalize(answers, complete=True)
        from backend.modules.hr.schema_v2 import review_issues
        issues = review_issues(out)
        self.assertIn('Označeno k upřesnění: Místo narození (obec)', issues)
        self.assertTrue(any('Platí za mě pojistné' in i for i in issues))
        c = self.save(self.create(), answers)
        c = self.transition(c, 'submit', 'employee-a').json()
        snapshot = self.call('GET', f"/cases/{c['id']}/submissions/1").json()['snapshot']
        self.assertEqual(snapshot['answers']['_review'], ['birth_place'])
        self.assertIn('Označeno k upřesnění: Místo narození (obec)', snapshot['issues'])

    def test_submit_requires_attestation(self):
        c = self.save(self.create())
        self.assertEqual(self.transition(c, 'submit', 'employee-a', confirmed=False).status_code, 422)

    # --- two companies, two concurrent contracts ---------------------------
    def test_one_person_two_companies_two_cases_isolated(self):
        a = self.create('work-a')
        b = self.create('work-a2', 'hr-b')
        self.assertNotEqual(a['context']['entity_id'], b['context']['entity_id'])
        self.assertEqual(a['context']['person_id'], b['context']['person_id'])
        self.assertEqual(self.call('GET', f"/cases/{b['id']}", user='hr-a').status_code, 404)
        self.assertEqual(self.call('GET', f"/cases/{a['id']}", user='hr-b').status_code, 404)
        self.assertEqual(self.call('GET', f"/cases/{a['id']}/export", user='hr-b').status_code, 404)
        both = {c['id'] for c in self.call('GET', '/cases', user='employee-a').json()}
        self.assertEqual(both, {a['id'], b['id']})

    # --- returning a specific field, version conflict -----------------------
    def test_return_specific_field_and_stale_write(self):
        c = self.save(self.create())
        c = self.transition(c, 'submit', 'employee-a').json()
        c = self.transition(c, 'return', note='Pole „Trvalý pobyt: PSČ“ – doplňte prosím správné PSČ.').json()
        stale = c['version']
        c = self.save(c, {**COMPLETE, 'perm_zip': '440 02'})
        r = self.call('PUT', f"/cases/{c['id']}/draft", dict(expected_version=stale, answers=COMPLETE), 'employee-a')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.call('GET', f"/cases/{c['id']}").json()['answers']['perm_zip'], '440 02')

    # --- legacy template remains readable/editable -------------------------
    def test_v1_case_stays_readable_and_editable_under_its_validator(self):
        with self.Session.begin() as db:
            e = db.get(Employment, 'work-b')
            db.add(HRCase(id='legacy-case', employment_id='work-b', open_key='work-b', request_key='legacy-request-key-0001',
                          created_by='hr-b', template_version=V1, hr_owner_id='hr-b',
                          context=dict(person_id=e.person_id, entity_id=e.entity_id, employment_id=e.id, name='x',
                                       employer='Test B', ico='00000002', position='x', employment_type='HPP', start='2026-01-01'),
                          draft=dict(first_name='Stará', last_name='Verze', address_permanent='Ulice 1'), requirements=[]))
        c = self.call('GET', '/cases/legacy-case', user='hr-b').json()
        self.assertEqual(c['template_version'], V1)
        self.assertEqual(c['answers']['address_permanent'], 'Ulice 1')
        self.assertTrue(any(f['key'] == 'address_permanent' for s in c['sections'] for f in s['fields']))
        v1_complete = dict(first_name='Stará', last_name='Verze', birth_date='1980-01-01', citizenship='CZ',
                           address_permanent='Ulice 2', personal_id_status='not_assigned', health_insurance='111',
                           tax_residency='CZ', declaration='no')
        r = self.call('PUT', '/cases/legacy-case/draft', dict(expected_version=c['version'], answers=v1_complete), 'employee-b')
        self.assertEqual(r.status_code, 200, r.text)
        r = self.transition(r.json(), 'submit', 'employee-b', confirmed=False)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.call('GET', '/cases/legacy-case/submissions/1', user='hr-b').json()['snapshot']['template_version'], V1)
        self.assertEqual(VERSION, 'cz-existing-2026.11-v2')

    # --- payroll ownership --------------------------------------------------
    def test_payroll_receipt_only_by_designated_finance_person(self):
        c = self.complete_case(answers=COMPLETE)
        # owner/admin rights never imitate the accountant
        self.assertEqual(self.transition(c, 'payroll_receive', 'owner', confirmed=True).status_code, 403)
        unassigned = self.create('work-b', 'hr-b')
        self.assertIsNone(unassigned['owners']['payroll'])
        self.assertEqual(self.call('PUT', f"/cases/{unassigned['id']}/owners",
                                   dict(expected_version=unassigned['version'], hr_owner_id='hr-b',
                                        payroll_owner_id='finance-a'), 'hr-b').status_code, 422)
        received = self.transition(c, 'payroll_receive', 'finance-a', confirmed=True)
        self.assertEqual(received.status_code, 200, received.text)
        c = received.json()
        self.assertEqual(self.transition(c, 'payroll_import', 'finance-a', confirmed=True, note='').status_code, 409)
        c = self.transition(c, 'payroll_import', 'finance-a', confirmed=True, note='Import do mzdového programu X').json()
        c = self.transition(c, 'authority_filing', 'finance-a', confirmed=True, note='Přihláška ČSSZ č. 1').json()
        actions = [h['action'] for h in c['history']]
        self.assertEqual(actions[-3:], ['payroll_receive', 'payroll_import', 'authority_filing'])

    def test_hr_owner_must_hold_hr_role_for_company(self):
        r = self.call('POST', '/cases', dict(employment_id='work-a', request_key=str(uuid4()), hr_owner_id='hr-b'))
        self.assertEqual(r.status_code, 422)

    # --- export -------------------------------------------------------------
    def test_export_only_reviewed_revision_with_text_identifiers(self):
        draft = self.create()
        self.assertEqual(self.call('GET', f"/cases/{draft['id']}/export").status_code, 409)
        answers = {**COMPLETE, 'personal_id_status': 'assigned', 'personal_id': '736028/5163', 'perm_zip': '011 01',
                   '_review': ['birth_country']}
        self.call('POST', '/employments/work-a/terms', TERMS)
        c = self.save(draft, answers)
        c = self.transition(c, 'submit', 'employee-a').json()
        c = self.configure(c, False, 'pending').json()
        c = self.transition(c, 'review', confirmed=True).json()
        r = self.call('GET', f"/cases/{c['id']}/export?fmt=json", user='finance-a')
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn('POHODA ani PAMICA', data['notice'])
        self.assertEqual(data['case']['revision'], 1)
        values = {f['key']: f for f in data['fields']}
        self.assertEqual(values['personal_id']['value'], '736028/5163')
        self.assertEqual(values['perm_zip']['value'], '011 01')
        self.assertEqual(values['birth_country']['status'], 'review')
        self.assertTrue(any(u['kind'] == 'requirement' for u in data['unresolved']))
        self.assertEqual(data['hr_terms']['effective_from'], '2026-11-01')
        self.assertFalse(data['confirmations']['payroll_received'])
        bundle = self.call('GET', f"/cases/{c['id']}/export?fmt=zip").content
        names = set(zipfile.ZipFile(io.BytesIO(bundle)).namelist())
        self.assertEqual(names, {'export.json', 'udaje.csv', 'export.xlsx', 'doklady_manifest.json', 'nevyresene.csv', 'CTI_ME.txt'})
        from openpyxl import load_workbook
        sheet = load_workbook(io.BytesIO(zipfile.ZipFile(io.BytesIO(bundle)).read('export.xlsx')))['Údaje']
        row = next(r for r in sheet.iter_rows(values_only=True) if r[1] == 'perm_zip')
        self.assertEqual(row[3], '011 01')
        self.assertEqual(self.call('GET', f"/cases/{c['id']}/export", user='employee-a').status_code, 403)
        events = self.call('GET', f"/cases/{c['id']}/access-events").json()
        self.assertTrue(any(e['kind'] == 'export_created' for e in events))

    # --- HR internal terms ---------------------------------------------------
    def test_terms_are_hr_only_versioned_and_portal_sees_names(self):
        self.assertEqual(self.call('POST', '/employments/work-a/terms', TERMS, 'employee-a').status_code, 404)
        self.assertEqual(self.call('POST', '/employments/work-a/terms', TERMS, 'hr-b').status_code, 404)
        r = self.call('POST', '/employments/work-a/terms', TERMS)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.call('POST', '/employments/work-a/terms', TERMS).status_code, 409)
        r = self.call('POST', '/employments/work-a/terms', {**TERMS, 'expected_revision': 1, 'effective_from': '2027-01-01'})
        self.assertEqual(r.json()['current']['revision'], 2)
        c = self.create()
        own = self.call('GET', f"/cases/{c['id']}", user='employee-a').json()
        self.assertEqual(own['handover']['equipment'], ['Telefon'])
        self.assertEqual(own['handover']['car'], 'Testovací vůz')
        self.assertNotIn('terms', own)
        self.assertIn('terms', self.call('GET', f"/cases/{c['id']}").json())

    # --- wizard ----------------------------------------------------------------
    def test_wizard_creates_person_contact_and_explicit_employment(self):
        ents = self.call('GET', '/wizard/entities').json()
        self.assertEqual([e['id'] for e in ents['entities']], ['a'])
        self.assertFalse(ents['can_create'])
        key = str(uuid4())
        body = dict(request_key=key, entity_id='a', first_name='Nová', last_name='Osoba', birth_date='1995-05-05')
        person = self.call('POST', '/wizard/people', body).json()['person']
        self.assertEqual(self.call('POST', '/wizard/people', body).json()['person']['id'], person['id'])
        dup = self.call('POST', '/wizard/people', {**body, 'request_key': str(uuid4())})
        self.assertEqual(dup.status_code, 409)
        contact = dict(entity_id='a', source='work', email='nova.osoba@example.test',
                       verification='Ověřeno z přímé korespondence', confirmed=True)
        self.assertEqual(self.call('PUT', f"/wizard/people/{person['id']}/contact", contact).status_code, 404)
        employment = dict(entity_id='a', person_id=person['id'], employment_type='HPP', position='Koordinátorka',
                          date_start='2026-10-01', evidence='Synthetic contract', confirmed=False)
        self.assertEqual(self.call('POST', '/wizard/employments', employment).status_code, 422)
        r = self.call('POST', '/wizard/employments', {**employment, 'confirmed': True})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.call('POST', '/wizard/employments', {**employment, 'confirmed': True}).json()['employment_id'],
                         r.json()['employment_id'])
        self.assertEqual(self.call('POST', '/wizard/employments', {**employment, 'confirmed': True, 'entity_id': 'b'}).status_code, 404)
        r = self.call('PUT', f"/wizard/people/{person['id']}/contact", contact)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()['person']['contacts'][0]['address'], 'nova.osoba@example.test')
        clash = self.call('PUT', f"/wizard/people/{person['id']}/contact", {**contact, 'source': 'personal'})
        self.assertEqual(clash.status_code, 200)
        staff = self.call('GET', '/wizard/staff?entity_id=a').json()
        self.assertIn('finance-a', [p['id'] for p in staff['payroll']])
        self.assertNotIn('owner', [p['id'] for p in staff['payroll']])
        found = self.call('GET', '/wizard/people?entity_id=a&q=Nov').json()
        self.assertIn(person['id'], [p['id'] for p in found['people']])
        hidden = self.call('GET', '/wizard/people?entity_id=a&q=employee-b').json()
        self.assertEqual(hidden['hidden_matches'], 1)
        self.assertNotIn('employee-b', [p['id'] for p in hidden['people']])
        with self.Session() as db:
            self.assertEqual(db.query(AuditLog).filter_by(action='hr_employment_created').count(), 1)
            self.assertNotIn('nova.osoba@example.test', ' '.join(a.detail for a in db.query(AuditLog).all()))

    def test_entity_creation_requires_global_owner_and_valid_ico(self):
        body = dict(legal_name='Synthetic Castle s.r.o.', name='Synthetic Castle', code='SYN-C', ico='26690757',
                    source='Výpis z obchodního rejstříku')
        self.assertEqual(self.call('POST', '/wizard/entities', body).status_code, 403)
        self.assertEqual(self.call('POST', '/wizard/entities', body, 'owner').status_code, 422)
        self.assertEqual(self.call('POST', '/wizard/entities', {**body, 'ico': '26690756'}, 'owner').status_code, 200)
        self.assertEqual(self.call('POST', '/wizard/entities', {**body, 'ico': '26690756'}, 'owner').status_code, 409)

    def test_unknown_role_rows_do_not_break_authorization(self):
        from sqlalchemy import text
        with self.Session.begin() as db:
            db.execute(text("insert into role_assignment(id, person_id, role, scope_type, created_at) "
                            "values ('x-unknown', 'hr-a', 'PAYMENT_MARKER', 'ALL', '2026-01-01')"))
        self.assertEqual(self.call('GET', '/wizard/staff?entity_id=a').status_code, 200)
        self.assertEqual(self.create()['status'], 'draft')


class EntryGuardTests(fixtures.unittest.TestCase):
    def client(self, **kw):
        app = FastAPI()

        @app.api_route('/hr/api/{rest:path}', methods=['GET', 'POST', 'PUT'])
        def any_route(rest: str):
            return {'ok': True}
        self.now = [0.0]
        app.add_middleware(EntryGuard, clock=lambda: self.now[0], **kw)
        return TestClient(app)

    def test_code_requests_are_rate_limited_per_client(self):
        c = self.client()
        codes = [c.post('/hr/api/code', json={}, headers={'cf-connecting-ip': '198.51.100.1'}).status_code for _ in range(7)]
        self.assertEqual(codes[:6], [200] * 6)
        self.assertEqual(codes[6], 429)
        self.assertEqual(c.post('/hr/api/code', json={}, headers={'cf-connecting-ip': '198.51.100.2'}).status_code, 200)
        self.now[0] = 601
        self.assertEqual(c.post('/hr/api/code', json={}, headers={'cf-connecting-ip': '198.51.100.1'}).status_code, 200)

    def test_methods_and_sizes_are_bounded(self):
        c = self.client()
        self.assertEqual(c.delete('/hr/api/x').status_code, 405)
        self.assertEqual(c.post('/hr/api/x', content=b'x' * (128 * 1024 + 1)).status_code, 413)
        big_upload = c.post('/hr/api/cases/1/documents', content=b'x' * (1024 * 1024))
        self.assertEqual(big_upload.status_code, 200)


if __name__ == '__main__':
    fixtures.unittest.main()
