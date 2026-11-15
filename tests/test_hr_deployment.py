"""Only temporary synthetic databases and controlled SMTP/scanner probes."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from cryptography.fernet import Fernet
import test_hr_cases as fixtures
from backend.modules.hr.entry_app import create_app, PUBLIC_PATHS
from backend.modules.hr.startup import validate_database_location
from backend.modules.hr import readiness, runtime

SHA = 'a' * 40


class HRDeploymentTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        root = Path(self.temp.name)
        self.documents = root / 'documents'
        self.documents.mkdir(mode=0o700)
        self.database = root / 'synthetic.sqlite'
        self.settings = SimpleNamespace(secret_key='synthetic-deployment-key-not-for-production',
                                        database_url='sqlite:///' + str(self.database))
        self.engine = create_engine(self.settings.database_url, connect_args={'check_same_thread': False})
        fixtures.Base.metadata.create_all(self.engine)
        self.env = patch.dict(os.environ, {
            'NEXUS_HR_ENABLED': '1', 'NEXUS_HR_PUBLIC_ORIGIN': 'https://people.example',
            'NEXUS_HR_SMTP_HOST': 'mail.example', 'NEXUS_HR_SMTP_USER': 'synthetic-user',
            'NEXUS_HR_SMTP_PASSWORD': 'synthetic-sensitive-password', 'NEXUS_HR_SMTP_FROM': 'hr@example.test',
            'NEXUS_HR_SMTP_PORT': '465', 'NEXUS_HR_DOCUMENT_ROOT': str(self.documents),
            'NEXUS_HR_DOCUMENT_KEYS': Fernet.generate_key().decode(),
            'NEXUS_HR_CLAMD_SOCKET': '/synthetic/clamd.sock'})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.engine.dispose()
        self.temp.cleanup()

    def app(self):
        with patch('backend.config.get_settings', return_value=self.settings), \
                patch('backend.core.models.base.engine', self.engine):
            return create_app()

    def test_public_factory_exposes_only_employee_allowlist_and_assets(self):
        app = self.app()
        self.assertEqual({r.path for r in app.routes}, PUBLIC_PATHS | {'/static/hr/{asset}'})
        with TestClient(app, base_url='https://people.example') as client:
            entry = client.get('/hr/entry')
            self.assertEqual(entry.status_code, 200)
            self.assertEqual(entry.headers['cache-control'], 'no-store')
            self.assertEqual(client.get('/hr/api/meta').status_code, 401)
            for path in ['/people/hr', '/people', '/api/hr/cases', '/api/hr/meta', '/auth/login', '/login',
                         '/openapi.json', '/docs', '/redoc', '/import', '/health', '/static/hr/index.html',
                         '/static/hr/entry.html', '/static/hr/../index.html', '/static/hr/%2e%2e%2findex.html']:
                self.assertEqual(client.get(path).status_code, 404, path)
            for asset in ['app.js', 'style.css']:
                self.assertEqual(client.get('/static/hr/' + asset).status_code, 200)
            self.assertEqual(client.get('/hr/entry/').status_code, 404)
            self.assertEqual(client.get('/hr/entry', headers={'host': 'attacker.example'}).status_code, 403)

    def test_public_factory_does_not_issue_mail_or_write_database(self):
        before = hashlib.sha256(self.database.read_bytes()).hexdigest()
        with patch.object(runtime, 'send_code') as mail:
            with TestClient(self.app(), base_url='https://people.example') as client:
                client.get('/hr/entry')
                client.get('/hr/api/meta')
            mail.assert_not_called()
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(), before)

    def test_public_factory_rejects_missing_configuration(self):
        for variable in ['NEXUS_HR_ENABLED', 'NEXUS_HR_PUBLIC_ORIGIN', 'NEXUS_HR_SMTP_PASSWORD',
                         'NEXUS_HR_DOCUMENT_KEYS', 'NEXUS_HR_CLAMD_SOCKET']:
            with patch.dict(os.environ, {variable: ''}):
                with self.assertRaises(RuntimeError, msg=variable):
                    self.app()
        with patch.object(self.settings, 'secret_key', 'dev-secret-key-change-in-production'):
            with self.assertRaises(RuntimeError):
                self.app()

    def test_public_factory_refuses_missing_schema_without_creating_it(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql('DROP TABLE hr_invitation')
        before = self.database.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'schema'):
            self.app()
        self.assertEqual(self.database.read_bytes(), before)

    def test_database_target_must_be_existing_explicit_absolute_sqlite_file(self):
        validate_database_location(self.settings.database_url)
        missing = Path(self.temp.name) / 'must-not-be-created.db'
        for target in ['sqlite://', 'sqlite:///nexus.db', 'sqlite:///' + str(missing),
                       'postgresql://user:secret@db.example/nexus', self.settings.database_url + '?mode=ro']:
            with self.assertRaises(RuntimeError):
                validate_database_location(target)
        self.assertFalse(missing.exists())
        link = Path(self.temp.name) / 'alias.db'
        link.symlink_to(self.database)
        with self.assertRaises(RuntimeError):
            validate_database_location('sqlite:///' + str(link))

    def test_readiness_reads_schema_and_reports_unprobed_adapters_without_mutation(self):
        before = self.database.read_bytes()
        with patch.object(readiness, 'release_state', return_value=(SHA, True)), \
                patch.object(readiness, 'probe_mail') as mail, patch.object(readiness, 'probe_scanner') as scan:
            result = readiness.report(self.settings, SHA)
        self.assertTrue(result['checks_passed'])
        self.assertFalse(result['adapter_probes_passed'])
        self.assertFalse(result['production_ready'])
        self.assertEqual([c['status'] for c in result['checks'][-2:]], ['not_tested', 'not_tested'])
        mail.assert_not_called()
        scan.assert_not_called()
        self.assertEqual(self.database.read_bytes(), before)
        self.assertEqual(list(self.documents.iterdir()), [])

    def test_readiness_requires_exact_clean_revision(self):
        for state in [('b' * 40, True), (SHA, False)]:
            with patch.object(readiness, 'release_state', return_value=state):
                result = readiness.report(self.settings, SHA)
            self.assertFalse(result['checks_passed'])
            self.assertEqual(result['checks'][0]['status'], 'fail')

    def test_readiness_suppresses_adapter_exception_secrets_and_reports_failure(self):
        with patch.object(readiness, 'release_state', return_value=(SHA, True)), \
                patch.object(readiness, 'probe_mail', side_effect=RuntimeError('synthetic-sensitive-password')), \
                patch.object(readiness, 'probe_scanner', side_effect=ValueError(str(self.documents))):
            result = readiness.report(self.settings, SHA, probe_adapters=True)
        self.assertFalse(result['checks_passed'])
        self.assertFalse(result['adapter_probes_passed'])
        rendered = json.dumps(result)
        for secret in ['synthetic-sensitive-password', str(self.database), str(self.documents),
                       os.environ['NEXUS_HR_DOCUMENT_KEYS'], 'hr@example.test']:
            self.assertNotIn(secret, rendered)

    def test_mail_probe_authenticates_with_verified_tls_and_never_sends(self):
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        with patch.object(runtime.smtplib, 'SMTP_SSL', return_value=smtp) as connect:
            readiness.probe_mail()
        self.assertEqual(connect.call_args.kwargs['context'].verify_mode, runtime.ssl.CERT_REQUIRED)
        self.assertTrue(connect.call_args.kwargs['context'].check_hostname)
        smtp.login.assert_called_once_with('synthetic-user', 'synthetic-sensitive-password')
        smtp.send_message.assert_not_called()
        smtp.sendmail.assert_not_called()

    def test_scanner_probe_requires_clean_and_detected_results(self):
        with patch.object(runtime, 'scan_document', side_effect=['ClamAV synthetic', None]) as scan:
            readiness.probe_scanner()
        self.assertEqual(len(scan.call_args_list[1].args[0]), 68)
        for responses in [[None], ['ClamAV synthetic', 'ClamAV synthetic']]:
            with patch.object(runtime, 'scan_document', side_effect=responses):
                with self.assertRaises(ValueError):
                    readiness.probe_scanner()

    def test_successful_probes_do_not_claim_production_readiness(self):
        with patch.object(readiness, 'release_state', return_value=(SHA, True)), \
                patch.object(readiness, 'probe_mail'), patch.object(readiness, 'probe_scanner'):
            result = readiness.report(self.settings, SHA, probe_adapters=True)
        self.assertTrue(result['checks_passed'])
        self.assertTrue(result['adapter_probes_passed'])
        self.assertFalse(result['production_ready'])
        self.assertTrue(result['manual_checks_required'])
