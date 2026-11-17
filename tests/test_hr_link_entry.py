"""Private, case-bound invitations for employees whose email is not known yet."""
import os
from datetime import timedelta
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
import test_hr_cases as fixtures
import test_hr_entry_documents as entry_fixtures
from backend.core.models.kernel import Person
from backend.modules.hr.models import HRInvitation, HREvent
from backend.modules.hr.portal import now


class HRLinkEntryTests(TestCase):
    setUp = entry_fixtures.HREntryDocumentTests.setUp
    tearDown = entry_fixtures.HREntryDocumentTests.tearDown
    call = fixtures.HRCaseTests.call
    create = fixtures.HRCaseTests.create
    external = entry_fixtures.HREntryDocumentTests.external
    issue = entry_fixtures.HREntryDocumentTests.issue

    def without_email(self):
        with self.Session.begin() as db:
            person = db.get(Person, 'employee-a')
            person.email_personal = person.email_work = None

    def open_link(self, case=None):
        case, invitation, token = self.issue(case, source='link')
        response = self.external('POST', '/open', {'token': token})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['authentication'], 'invitation_link')
        case = self.external('GET', '/cases/' + case['id']).json()
        return case, invitation, token, response

    def test_no_email_or_mail_adapter_needed_for_issue_open_save_and_submit(self):
        self.without_email()
        with patch.dict(os.environ, {'NEXUS_HR_SMTP_PASSWORD': ''}):
            caps = self.call('GET', '/meta').json()['capabilities']
            self.assertTrue(caps['external_invitations'])
            self.assertFalse(caps['email_invitations'])
            case, invitation, _, response = self.open_link()
            self.assertEqual(invitation['invitation']['access_mode'], 'link')
            self.assertEqual(invitation['invitation']['recipient'], 'Soukromý odkaz')
            for flag in ['HttpOnly', 'Secure', 'SameSite=strict', 'Path=/hr']:
                self.assertIn(flag, response.headers['set-cookie'])
            answers = {**fixtures.COMPLETE, 'email': 'newly-entered@example.test'}
            saved = self.external('PUT', f"/cases/{case['id']}/draft",
                                  {'expected_version': case['version'], 'answers': answers})
            self.assertEqual(saved.status_code, 200, saved.text)
            result = self.external('POST', f"/cases/{case['id']}/actions", dict(
                expected_version=saved.json()['version'], revision=0, request_key=str(uuid4()),
                action='submit', confirmed=True))
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()['status'], 'submitted')
        self.assertEqual(self.deliveries, [])
        with self.Session() as db:
            self.assertIsNone(db.get(Person, 'employee-a').email_personal)
            events = [e.kind for e in db.query(HREvent).filter_by(case_id=case['id'])]
            self.assertIn('entry_opened_by_link', events)
            self.assertNotIn('entry_verified', events)

    def test_private_link_is_default_and_requires_direct_handover_confirmation(self):
        self.without_email()
        case = self.create()
        path = f"/cases/{case['id']}/invitations"
        body = dict(expected_version=case['version'], request_key=str(uuid4()), confirmed=False)
        self.assertEqual(self.call('POST', path, body).status_code, 422)
        result = self.call('POST', path, {**body, 'confirmed': True})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['invitation']['access_mode'], 'link')
        retry = self.call('POST', path, {**body, 'confirmed': True})
        self.assertEqual(retry.status_code, 200)
        self.assertIsNone(retry.json()['url'])

    def test_only_scoped_hr_can_issue_link(self):
        case = self.create()
        body = dict(expected_version=case['version'], request_key=str(uuid4()),
                    recipient_source='link', confirmed=True)
        for user in ['employee-a', 'finance-a', 'hr-b', 'expired']:
            with self.subTest(user=user):
                self.assertIn(self.call('POST', f"/cases/{case['id']}/invitations", body, user=user).status_code,
                              [403, 404])

    def test_link_open_has_no_authority_to_downgrade_existing_email_invitation(self):
        _, _, token = self.issue(source='personal')
        result = self.external('POST', '/open', {'token': token})
        self.assertEqual(result.json(), {'requires_code': True})
        self.assertNotIn('set-cookie', result.headers)
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)
        result = self.external('POST', '/open', {'token': token, 'recipient_source': 'link'})
        self.assertEqual(result.status_code, 422)
        self.assertEqual(self.deliveries, [])

    def test_link_request_cannot_send_or_consume_an_email_code(self):
        _, _, token = self.issue(source='link')
        self.assertEqual(self.external('POST', '/code', {'token': token}).status_code, 409)
        self.assertEqual(self.external('POST', '/verify', {'token': token, 'code': '12345678'}).status_code, 409)
        self.assertEqual(self.deliveries, [])

    def test_link_get_and_preview_do_not_open_a_session(self):
        _, _, token = self.issue(source='link')
        self.assertEqual(self.portal.get('/hr/entry#' + token).status_code, 200)
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)
        with self.Session() as db:
            self.assertIsNone(db.query(HRInvitation).one().session_hash)

    def test_invalid_expired_and_revoked_link_are_rejected(self):
        _, invitation, token = self.issue(source='link')
        self.assertEqual(self.external('POST', '/open', {'token': 'A' * 43}).status_code, 401)
        with self.Session.begin() as db:
            row = db.get(HRInvitation, invitation['invitation']['id'])
            row.expires_at = now() - timedelta(seconds=1)
        self.assertEqual(self.external('POST', '/open', {'token': token}).status_code, 401)
        with self.Session.begin() as db:
            row = db.get(HRInvitation, invitation['invitation']['id'])
            row.expires_at = now() + timedelta(days=1)
            row.revoked_at = now()
        self.assertEqual(self.external('POST', '/open', {'token': token}).status_code, 401)

    def test_private_link_stays_case_scoped_and_preserves_csrf(self):
        other = self.create('work-a2', 'hr-b')
        case, _, token, _ = self.open_link()
        self.assertEqual(self.external('GET', '/cases/' + other['id']).status_code, 404)
        self.assertEqual(self.external('GET', '/cases').status_code, 404)
        self.assertFalse(case['permissions']['hr'])
        self.assertFalse(case['permissions']['payroll'])
        self.assertEqual(self.external('PUT', f"/cases/{case['id']}/draft",
            {'expected_version': case['version'], 'answers': fixtures.COMPLETE}, csrf=False).status_code, 403)
        self.assertEqual(self.portal.post('/hr/api/open', json={'token': token},
            headers={'Origin': 'https://attacker.example', 'X-HR-Portal': '1'}).status_code, 403)
        self.assertEqual(self.portal.post('/hr/api/open', json={'token': token},
            headers={'Origin': 'https://people.example'}).status_code, 403)

    def test_reopening_rotates_session_and_logout_needs_original_link(self):
        case, _, token, _ = self.open_link()
        old_cookie = self.portal.cookies.get('hr_entry')
        self.assertEqual(self.external('POST', '/open', {'token': token}).status_code, 200)
        self.assertNotEqual(self.portal.cookies.get('hr_entry'), old_cookie)
        with TestClient(self.client.app, base_url='https://people.example') as old:
            self.assertEqual(old.get('/hr/api/meta', headers={'Cookie': 'hr_entry=' + old_cookie}).status_code, 401)
        self.assertEqual(self.external('POST', '/logout', {}).status_code, 200)
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)
        self.assertEqual(self.external('POST', '/open', {'token': token}).status_code, 200)
        self.assertEqual(self.portal.get('/hr/api/meta').json()['case_id'], case['id'])

    def test_replacement_closes_old_link_and_session(self):
        case, _, old_token, _ = self.open_link()
        _, second, new_token = self.issue(case, source='link')
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)
        self.assertEqual(self.external('POST', '/open', {'token': old_token}).status_code, 401)
        self.assertEqual(self.external('POST', '/open', {'token': new_token}).status_code, 200)
        result = self.call('POST', f"/cases/{case['id']}/invitations/{second['invitation']['id']}/revoke",
                           {'expected_version': second['case_version']})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)

    def test_unknown_invitation_mode_and_inactive_person_fail_closed(self):
        _, invitation, token = self.issue(source='link')
        with self.Session.begin() as db:
            row = db.get(HRInvitation, invitation['invitation']['id'])
            row.recipient_source = 'unknown'
        self.assertEqual(self.external('POST', '/open', {'token': token}).status_code, 401)
        with self.Session.begin() as db:
            db.get(HRInvitation, invitation['invitation']['id']).recipient_source = 'link'
            db.get(Person, 'employee-a').is_active = False
        self.assertEqual(self.external('POST', '/open', {'token': token}).status_code, 401)
