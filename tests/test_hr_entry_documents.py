"""Synthetic integration tests; mail and antivirus delivery are controlled doubles."""
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import quote
from uuid import uuid4
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
import test_hr_cases as fixtures
COMPLETE = fixtures.COMPLETE
from backend.modules.hr.portal import router as portal_router, now
from backend.modules.hr.boundary import HRBoundary
from backend.modules.hr.models import HRCase, HRDocument, HRSubmission, HRInvitation, HREvent
from backend.core.models.kernel import Person, RoleAssignment, NexusRole, ScopeType
from backend.modules.hr import runtime

PDF = b'%PDF-1.4\nSynthetic test content, not a real employee document.\n%%EOF'


class HREntryDocumentTests(TestCase):
    # Share setup/helpers, not the 20 inherited test methods or their count.
    call = fixtures.HRCaseTests.call
    create = fixtures.HRCaseTests.create
    save = fixtures.HRCaseTests.save
    transition = fixtures.HRCaseTests.transition
    submitted = fixtures.HRCaseTests.submitted
    configure = fixtures.HRCaseTests.configure
    reviewed = fixtures.HRCaseTests.reviewed

    def setUp(self):
        fixtures.HRCaseTests.setUp(self)
        self.temp = TemporaryDirectory()
        self.keys = Fernet.generate_key().decode()
        self.env = patch.dict(os.environ, {
            'NEXUS_HR_DOCUMENT_ROOT': self.temp.name, 'NEXUS_HR_DOCUMENT_KEYS': self.keys,
            'NEXUS_HR_CLAMD_SOCKET': '/synthetic/scanner.sock',
            'NEXUS_HR_PUBLIC_ORIGIN': 'https://people.example',
            'NEXUS_HR_SMTP_HOST': 'mail.example', 'NEXUS_HR_SMTP_PORT': '465',
            'NEXUS_HR_SMTP_USER': 'synthetic', 'NEXUS_HR_SMTP_PASSWORD': 'synthetic',
            'NEXUS_HR_SMTP_FROM': 'hr@example.test'})
        self.env.start()
        self.client.app.include_router(portal_router)
        self.client.app.add_middleware(HRBoundary)
        self.portal = TestClient(self.client.app, base_url='https://people.example')
        self.deliveries = []
        self.mail = patch.object(runtime, 'send_code', side_effect=lambda address, code: self.deliveries.append((address, code)))
        self.scan = patch.object(runtime, 'scan_document', return_value='ClamAV synthetic test adapter')
        self.mail.start()
        self.scan.start()
        with self.Session.begin() as db:
            db.get(Person, 'employee-a').email_personal = 'employee@example.test'
            db.get(Person, 'employee-a').email_work = 'employee@work.example'

    def tearDown(self):
        self.portal.close()
        self.scan.stop()
        self.mail.stop()
        self.env.stop()
        self.temp.cleanup()
        fixtures.HRCaseTests.tearDown(self)

    def issue(self, case=None, source='personal'):
        case = case or self.create()
        r = self.call('POST', f"/cases/{case['id']}/invitations", dict(expected_version=case['version'],
            request_key=str(uuid4()), recipient_source=source, confirmed=True))
        self.assertEqual(r.status_code, 200, r.text)
        return case, r.json(), r.json()['url'].split('#')[1]

    def external(self, method, path, body=None, csrf=True):
        headers = {'Origin': 'https://people.example', 'X-HR-Portal': '1'}
        if csrf:
            r = self.portal.get('/hr/api/meta')
            if r.status_code == 200:
                headers['X-HR-CSRF'] = r.json()['csrf']
        return self.portal.request(method, '/hr/api' + path, json=body, headers=headers)

    def login(self, case=None):
        case, invitation, token = self.issue(case)
        r = self.external('POST', '/code', {'token': token})
        self.assertEqual(r.status_code, 200, r.text)
        r = self.external('POST', '/verify', {'token': token, 'code': self.deliveries[-1][1]})
        self.assertEqual(r.status_code, 200, r.text)
        return self.external('GET', '/cases/' + case['id']).json(), invitation, token, r

    def upload(self, case, data=PDF, user='employee-a', file_name='doklad.pdf', media='application/pdf',
               request_key=None, purpose='payroll_docs', external=False, expected_version=None):
        headers = {'Content-Type': media, 'X-HR-File-Name': quote(file_name),
                   'X-HR-Requirement': purpose, 'X-HR-Request-Key': request_key or str(uuid4()),
                   'X-HR-Expected-Version': str(expected_version or case['version'])}
        if external:
            headers.update({'Origin': 'https://people.example', 'X-HR-Portal': '1',
                            'X-HR-CSRF': self.portal.get('/hr/api/meta').json()['csrf']})
            return self.portal.post(f"/hr/api/cases/{case['id']}/documents", content=data, headers=headers)
        headers.update({'Authorization': 'Bearer ' + user, 'X-HR-CSRF': self.call('GET', '/meta', user=user).json()['csrf']})
        return self.client.post(f"/api/hr/cases/{case['id']}/documents", content=data, headers=headers)

    def test_invitation_scope_contact_confirmation_and_defaults(self):
        case = self.create()
        body = dict(expected_version=case['version'], request_key=str(uuid4()), recipient_source='personal', confirmed=True)
        path = f"/cases/{case['id']}/invitations"
        for user in ['employee-a', 'finance-a', 'hr-b', 'expired']:
            self.assertIn(self.call('POST', path, body, user=user).status_code, [403, 404])
        self.assertEqual(self.call('POST', path, {**body, 'confirmed': False}).status_code, 422)
        self.assertEqual(self.call('POST', path, {**body, 'recipient': 'unapproved@example.test'}).status_code, 422)
        with patch.dict(os.environ, {'NEXUS_HR_PUBLIC_ORIGIN': ''}):
            self.assertEqual(self.call('POST', path, body).status_code, 503)
        self.assertEqual(self.deliveries, [])

    def test_link_is_fragment_only_and_creation_never_sends_email(self):
        case, invitation, token = self.issue()
        self.assertNotIn('?', invitation['url'])
        self.assertEqual(self.deliveries, [])
        self.assertEqual(len(token), 43)
        with self.Session() as db:
            row = db.get(HRInvitation, invitation['invitation']['id'])
            self.assertEqual(row.token_hash, hashlib.sha256(token.encode()).hexdigest())
            self.assertNotIn(token, repr(row.__dict__))
        self.assertEqual(self.portal.get('/hr/entry').status_code, 200)
        self.assertEqual(self.deliveries, [])
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)

    def test_single_use_code_secure_cookie_and_no_nexus_access(self):
        case, invitation, token, verified = self.login()
        cookie = verified.headers['set-cookie']
        for expected in ['HttpOnly', 'Secure', 'SameSite=strict', 'Path=/hr']:
            self.assertIn(expected, cookie)
        self.assertNotIn('nexus_token', cookie)
        self.assertEqual(self.external('POST', '/verify', {'token': token, 'code': self.deliveries[-1][1]}).status_code, 401)
        self.assertEqual(self.portal.get('/api/hr/cases').status_code, 401)
        self.assertFalse(case['permissions']['hr'])
        self.assertFalse(case['permissions']['payroll'])

    def test_portal_cannot_cross_cases_even_with_same_person_or_hr_role(self):
        other = self.create('work-a2', 'hr-b')
        with self.Session.begin() as db:
            db.add(RoleAssignment(person_id='employee-a', role=NexusRole.OWNER, scope_type=ScopeType.ALL))
        case, _, _, _ = self.login()
        self.assertEqual(self.external('GET', '/cases/' + other['id']).status_code, 404)
        self.assertEqual(self.external('GET', '/cases').status_code, 404)
        self.assertEqual(self.external('PUT', f"/cases/{case['id']}/requirements", {}).status_code, 404)
        self.assertEqual(self.external('POST', f"/cases/{case['id']}/actions", dict(expected_version=case['version'],
            revision=0, action='review', confirmed=True, request_key=str(uuid4()))).status_code, 403)

    def test_portal_origin_csrf_and_json_limit_include_private_errors(self):
        case, _, token, _ = self.login()
        headers = {'Origin': 'https://attacker.example', 'X-HR-Portal': '1'}
        self.assertEqual(self.portal.post('/hr/api/code', json={'token': token}, headers=headers).status_code, 403)
        r = self.external('PUT', f"/cases/{case['id']}/draft", {'expected_version': case['version'], 'answers': COMPLETE}, csrf=False)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.headers['cache-control'], 'no-store')
        self.assertEqual(r.headers['referrer-policy'], 'no-referrer')
        r = self.portal.post('/hr/api/code', content=b'x' * (128 * 1024 + 1), headers={'Content-Type': 'application/json'})
        self.assertEqual(r.status_code, 413)
        self.assertEqual(r.headers['cache-control'], 'no-store')
        self.assertEqual(self.client.get('/hr/entry').status_code, 403)

    def test_code_attempts_are_bounded_and_resend_is_limited(self):
        case, invitation, token = self.issue()
        self.assertEqual(self.external('POST', '/code', {'token': token}).status_code, 200)
        self.assertEqual(self.external('POST', '/code', {'token': token}).status_code, 429)
        wrong = '00000000' if self.deliveries[-1][1] != '00000000' else '11111111'
        for _ in range(6):
            self.assertEqual(self.external('POST', '/verify', {'token': token, 'code': wrong}).status_code, 401)
        with self.Session.begin() as db:
            row = db.get(HRInvitation, invitation['invitation']['id'])
            self.assertEqual(row.code_attempts, 5)
            self.assertEqual(row.failed_attempts, 5)
            row.last_send_at = now() - timedelta(seconds=61)
            row.sends = 10
        self.assertEqual(self.external('POST', '/code', {'token': token}).status_code, 429)

    def test_failed_delivery_does_not_return_or_leave_a_valid_code(self):
        case, invitation, token = self.issue()
        with patch.object(runtime, 'send_code', side_effect=OSError('synthetic failure')):
            r = self.external('POST', '/code', {'token': token})
        self.assertEqual(r.status_code, 503)
        self.assertNotIn('synthetic failure', r.text)
        with self.Session() as db:
            row = db.get(HRInvitation, invitation['invitation']['id'])
            self.assertIsNone(row.code_digest)
            self.assertEqual(row.sends, 1)

    def test_invitation_replacement_and_revocation_invalidate_open_session(self):
        case, first, token, _ = self.login()
        _, second, new_token = self.issue(case)
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)
        self.assertEqual(self.external('POST', '/code', {'token': token}).status_code, 401)
        r = self.call('POST', f"/cases/{case['id']}/invitations/{second['invitation']['id']}/revoke", {'expected_version': second['case_version']})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.external('POST', '/code', {'token': new_token}).status_code, 401)

    def test_expired_session_and_invitation_are_rejected(self):
        case, invitation, token, _ = self.login()
        with self.Session.begin() as db:
            row = db.get(HRInvitation, invitation['invitation']['id'])
            row.session_expires_at = now() - timedelta(seconds=1)
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)
        with self.Session.begin() as db:
            db.get(HRInvitation, invitation['invitation']['id']).expires_at = now() - timedelta(seconds=1)
        self.assertEqual(self.external('POST', '/code', {'token': token}).status_code, 401)

    def test_recipient_change_immediately_invalidates_invitation_and_session(self):
        _, _, token, _ = self.login()
        with self.Session.begin() as db:
            db.get(Person, 'employee-a').email_personal = 'corrected@example.test'
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)
        self.assertEqual(self.external('POST', '/code', {'token': token}).status_code, 401)

    def test_expired_code_and_lifetime_attempt_budget_are_rejected(self):
        _, invitation, token = self.issue()
        self.external('POST', '/code', {'token': token})
        with self.Session.begin() as db:
            db.get(HRInvitation, invitation['invitation']['id']).code_expires_at = now() - timedelta(seconds=1)
        self.assertEqual(self.external('POST', '/verify', {'token': token, 'code': self.deliveries[-1][1]}).status_code, 401)
        with self.Session.begin() as db:
            row = db.get(HRInvitation, invitation['invitation']['id'])
            row.last_send_at = now() - timedelta(seconds=61)
            row.failed_attempts = 20
        self.assertEqual(self.external('POST', '/code', {'token': token}).status_code, 401)

    def test_logout_and_payroll_receipt_close_entry(self):
        case, _, _, _ = self.login()
        self.assertEqual(self.external('POST', '/logout', {}).status_code, 200)
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)
        case, _, _, _ = self.login(case)
        case = self.save(case)
        case = self.transition(case, 'submit', 'employee-a').json()
        case = self.configure(case).json()
        case = self.transition(case, 'review', confirmed=True).json()
        self.assertEqual(self.transition(case, 'payroll_receive', 'finance-a', confirmed=True).status_code, 200)
        self.assertEqual(self.portal.get('/hr/api/meta').status_code, 401)

    def test_portal_saves_uploads_submits_without_replacing_master_person(self):
        case, _, _, _ = self.login()
        case = self.external('PUT', f"/cases/{case['id']}/draft", {'expected_version': case['version'], 'answers': COMPLETE}).json()
        r = self.upload(case, external=True)
        self.assertEqual(r.status_code, 200, r.text)
        case = r.json()
        r = self.external('POST', f"/cases/{case['id']}/actions", dict(expected_version=case['version'], revision=0,
            request_key=str(uuid4()), action='submit'))
        self.assertEqual(r.status_code, 200, r.text)
        with self.Session() as db:
            snap = db.query(HRSubmission).filter_by(case_id=case['id']).one()
            self.assertEqual(snap.snapshot['documents'][0]['sha256'], hashlib.sha256(PDF).hexdigest())
            self.assertEqual(db.get(Person, 'employee-a').first_name, 'Testovací')

    def test_documents_encrypted_private_scoped_and_audited(self):
        case = self.create()
        r = self.upload(case)
        self.assertEqual(r.status_code, 200, r.text)
        doc = r.json()['documents'][0]
        files = list(Path(self.temp.name).iterdir())
        self.assertEqual(len(files), 1)
        self.assertNotIn(PDF, files[0].read_bytes())
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        path = f"/cases/{case['id']}/documents/{doc['id']}"
        self.assertEqual(self.call('GET', path, user='hr-b').status_code, 404)
        downloaded = self.call('GET', path, user='finance-a')
        self.assertEqual(downloaded.content, PDF)
        self.assertIn('attachment', downloaded.headers['content-disposition'])
        events = self.call('GET', f"/cases/{case['id']}/access-events").json()
        self.assertEqual([x['kind'] for x in events], ['document_uploaded', 'document_downloaded'])

    def test_document_type_filename_size_empty_and_purpose_rejected(self):
        case = self.create()
        for kwargs, expected in [({'data': b'not a PDF'}, 415), ({'file_name': '../doklad.pdf'}, 422),
                                 ({'file_name': 'file.html', 'media': 'text/html'}, 415),
                                 ({'data': b''}, 422), ({'purpose': 'unknown'}, 422),
                                 ({'data': b'%PDF-' + b'x' * runtime.MAX_DOCUMENT_BYTES}, 413)]:
            r = self.upload(case, **kwargs)
            self.assertEqual(r.status_code, expected, r.text)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_scan_failures_never_store_documents(self):
        case = self.create()
        with patch.object(runtime, 'scan_document', return_value=None):
            self.assertEqual(self.upload(case).status_code, 422)
        with patch.object(runtime, 'scan_document', side_effect=OSError('unavailable')):
            self.assertEqual(self.upload(case).status_code, 503)
        with patch.dict(os.environ, {'NEXUS_HR_DOCUMENT_KEYS': ''}):
            self.assertEqual(self.upload(case).status_code, 503)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])
        with self.Session() as db:
            self.assertEqual(db.query(HRDocument).count(), 0)

    def test_upload_replay_and_stale_version_cannot_duplicate_or_overwrite(self):
        case = self.create()
        request_key = str(uuid4())
        first = self.upload(case, request_key=request_key)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.upload(case, request_key=request_key).json()['documents'], first.json()['documents'])
        self.assertEqual(self.upload(case, request_key=request_key, data=PDF + b'changed').status_code, 409)
        self.assertEqual(self.upload(case).status_code, 409)
        self.assertEqual(len(list(Path(self.temp.name).iterdir())), 1)

    def test_upload_rechecks_concurrent_case_change_after_scan(self):
        case = self.create()
        def concurrent_change(data):
            with self.Session.begin() as db:
                db.get(HRCase, case['id']).version += 1
            return 'ClamAV synthetic'
        with patch.object(runtime, 'scan_document', side_effect=concurrent_change):
            self.assertEqual(self.upload(case).status_code, 409)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_failed_document_transaction_removes_unreferenced_ciphertext(self):
        from fastapi import HTTPException
        case = self.create()
        with patch('backend.modules.hr.routes.commit', side_effect=HTTPException(409, 'Synthetic conflict')):
            self.assertEqual(self.upload(case).status_code, 409)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])
        with self.Session() as db:
            self.assertEqual(db.query(HRDocument).count(), 0)

    def test_document_key_rotation_keeps_existing_evidence_readable(self):
        case = self.upload(self.create()).json()
        doc = case['documents'][0]
        path = f"/cases/{case['id']}/documents/{doc['id']}"
        new_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'NEXUS_HR_DOCUMENT_KEYS': new_key + ',' + self.keys}):
            self.assertEqual(self.call('GET', path).content, PDF)
        with patch.dict(os.environ, {'NEXUS_HR_DOCUMENT_KEYS': new_key}):
            self.assertEqual(self.call('GET', path).status_code, 503)

    def test_portal_upload_rechecks_revocation_after_scan(self):
        case, invitation, _, _ = self.login()
        def revoke_in_scan(data):
            with self.Session.begin() as db:
                db.get(HRInvitation, invitation['invitation']['id']).revoked_at = now()
            return 'ClamAV synthetic'
        with patch.object(runtime, 'scan_document', side_effect=revoke_in_scan):
            self.assertEqual(self.upload(case, external=True).status_code, 401)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_document_immutable_revision_survives_withdrawal(self):
        case = self.save(self.create())
        case = self.upload(case).json()
        doc = case['documents'][0]
        case = self.transition(case, 'submit', 'employee-a').json()
        first = self.call('GET', f"/cases/{case['id']}/submissions/1").json()
        self.assertEqual(self.upload(case).status_code, 409)
        case = self.transition(case, 'return', note='Prosíme čitelnější kopii.').json()
        case = self.call('POST', f"/cases/{case['id']}/documents/{doc['id']}/withdraw", {'expected_version': case['version']}, user='employee-a').json()
        self.assertEqual(case['documents'], [])
        self.assertEqual(self.call('GET', f"/cases/{case['id']}/submissions/1").json(), first)
        self.assertEqual(self.transition(case, 'submit', 'employee-a').status_code, 200)
        second = self.call('GET', f"/cases/{case['id']}/submissions/2").json()
        self.assertNotEqual(second['sha256'], first['sha256'])
        self.assertEqual(second['snapshot']['documents'], [])

    def test_evidence_reference_is_case_bound_and_prevents_withdrawal(self):
        case = self.upload(self.create()).json()
        doc_id = case['documents'][0]['id']
        other = self.create('work-b', 'hr-b')
        body = dict(expected_version=other['version'], confirmed=True,
                    items=[dict(id='payroll', label='Test', blocks_payroll=True, status='verified', evidence_ref='document:' + doc_id)])
        self.assertEqual(self.call('PUT', f"/cases/{other['id']}/requirements", body, user='hr-b').status_code, 422)
        case = self.configure(case, True, 'verified', 'document:' + doc_id).json()
        self.assertEqual(self.call('POST', f"/cases/{case['id']}/documents/{doc_id}/withdraw", {'expected_version': case['version']}, user='employee-a').status_code, 409)

    def test_missing_or_corrupt_ciphertext_fails_closed(self):
        case = self.upload(self.create()).json()
        doc = case['documents'][0]
        path = Path(self.temp.name) / (doc['id'] + '.enc')
        path.write_bytes(b'corrupted')
        self.assertEqual(self.call('GET', f"/cases/{case['id']}/documents/{doc['id']}").status_code, 503)

    def test_storage_root_and_upload_roles_are_restricted(self):
        case = self.create()
        self.assertEqual(self.upload(case, user='finance-a').status_code, 403)
        self.assertEqual(self.upload(case, user='hr-b').status_code, 404)
        with patch.dict(os.environ, {'NEXUS_HR_DOCUMENT_ROOT': str(Path(__file__).resolve().parents[1])}):
            self.assertFalse(runtime.uploads_ready())
        Path(self.temp.name).chmod(0o755)
        self.assertFalse(runtime.uploads_ready())

    def test_invitation_optimistic_lock_rejects_concurrent_consumption(self):
        from backend.modules.hr.routes import commit
        from fastapi import HTTPException
        _, invitation, _ = self.issue()
        with self.Session() as a, self.Session() as b:
            left = a.get(HRInvitation, invitation['invitation']['id'])
            right = b.get(HRInvitation, invitation['invitation']['id'])
            left.failed_attempts += 1
            right.failed_attempts += 1
            commit(a)
            with self.assertRaises(HTTPException) as raised:
                commit(b)
            self.assertEqual(raised.exception.status_code, 409)


class HRScannerProtocolTests(TestCase):
    def test_real_unix_socket_framing_sends_exact_file_and_accepts_clean_receipt(self):
        import socket
        import struct
        import threading
        received = []
        with TemporaryDirectory() as directory:
            path = str(Path(directory) / 'clamd.sock')
            try:
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            except PermissionError:
                self.skipTest('This executor does not permit Unix sockets; run the transport check in staging.')
            server.bind(path)
            server.listen(2)
            server.settimeout(3)
            errors = []
            def exact(connection, size):
                data = b''
                while len(data) < size:
                    chunk = connection.recv(size - len(data))
                    if not chunk:
                        raise ValueError('Short request')
                    data += chunk
                return data
            def serve():
                try:
                    for command in [b'zVERSION\0', b'zINSTREAM\0']:
                        with server.accept()[0] as connection:
                            connection.settimeout(3)
                            self.assertEqual(exact(connection, len(command)), command)
                            if command == b'zINSTREAM\0':
                                content = bytearray()
                                while True:
                                    length = struct.unpack('!I', exact(connection, 4))[0]
                                    if not length:
                                        break
                                    content.extend(exact(connection, length))
                                received.append(bytes(content))
                                connection.sendall(b'stream: OK\0')
                            else:
                                connection.sendall(b'ClamAV synthetic protocol fixture\0')
                except Exception as exc:
                    errors.append(exc)
            worker = threading.Thread(target=serve, daemon=True)
            worker.start()
            try:
                with patch.dict(os.environ, {'NEXUS_HR_CLAMD_SOCKET': path}):
                    self.assertEqual(runtime.scan_document(PDF), 'ClamAV synthetic protocol fixture')
            finally:
                worker.join(timeout=4)
                server.close()
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(received, [PDF])

    def test_scanner_detection_error_or_unknown_reply_is_never_clean(self):
        for reply in [b'stream: Synthetic FOUND', b'stream: ERROR', b'OK']:
            with patch.object(runtime, 'clamd_command', side_effect=[b'ClamAV synthetic', reply]):
                if reply.endswith(b' FOUND'):
                    self.assertIsNone(runtime.scan_document(PDF))
                else:
                    with self.assertRaises(ValueError):
                        runtime.scan_document(PDF)

    def test_scanner_transport_frames_bytes_and_rejects_truncated_reply(self):
        import struct
        from unittest.mock import MagicMock
        sock = MagicMock()
        sock.__enter__.return_value = sock
        sock.recv.side_effect = [b'stream: ', b'OK\0']
        with patch.dict(os.environ, {'NEXUS_HR_CLAMD_SOCKET': '/synthetic/clamd.sock'}), patch.object(runtime.socket, 'socket', return_value=sock):
            self.assertEqual(runtime.clamd_command(b'INSTREAM', PDF), b'stream: OK')
        payload = b''.join(call.args[0] for call in sock.sendall.call_args_list)
        self.assertEqual(payload, b'zINSTREAM\0' + struct.pack('!I', len(PDF)) + PDF + b'\0\0\0\0')
        sock.recv.side_effect = [b'']
        with patch.dict(os.environ, {'NEXUS_HR_CLAMD_SOCKET': '/synthetic/clamd.sock'}), patch.object(runtime.socket, 'socket', return_value=sock):
            with self.assertRaises(ValueError):
                runtime.clamd_command(b'INSTREAM', PDF)
