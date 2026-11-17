"""Read-only release checks. No employee rows, credentials or exception text in output."""
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from . import runtime
from .startup import validate_database_location, validate_schema, hr_signing_key


def release_state():
    root = Path(__file__).resolve().parents[3]
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, timeout=5,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    revision = git('rev-parse', 'HEAD')
    if not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('Invalid release revision.')
    return revision, not bool(git('status', '--porcelain', '--untracked-files=no'))


def check_database(database_url):
    validate_database_location(database_url)
    path = Path(make_url(database_url).database)
    # URI mode=ro cannot create or migrate the selected database, even on error.
    engine = create_engine('sqlite://', creator=lambda: sqlite3.connect(
        path.as_uri() + '?mode=ro', uri=True, timeout=5))
    try:
        validate_schema(engine)
    finally:
        engine.dispose()


def probe_mail():
    if runtime.transport() == 'outbox':
        # An empty body is rejected by validation (422) only after authorization passed;
        # 403 means the HR service is not allowed to send. Nothing is ever sent here.
        opener = runtime.urllib.request.build_opener(runtime.urllib.request.ProxyHandler({}))
        request = runtime.urllib.request.Request(runtime.outbox_config(), data=b'{}', method='POST',
                                                 headers={'Content-Type': 'application/json',
                                                          **runtime.outbox_headers()})
        try:
            opener.open(request, timeout=10)
        except runtime.urllib.error.HTTPError as exc:
            if exc.code == 422:
                return
        raise ValueError('Outbox refused the HR service.')
    if runtime.transport() == 'graph':
        runtime.graph_token()  # authenticates the app over verified TLS; sends nothing
        return
    host, username, password, _, port = runtime.mail_config()
    with runtime.smtplib.SMTP_SSL(host, port, timeout=10,
                                 context=runtime.ssl.create_default_context()) as smtp:
        smtp.login(username, password)
    # Authentication is not an email deliverability test. Never send a message.


def probe_scanner():
    # Standard harmless EICAR test, sent in memory to the configured scanner.
    # https://www.eicar.org/download-anti-malware-testfile/
    eicar = (b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$'
             b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
    if not runtime.scan_document(b'NEXUS HR harmless deployment probe\n'):
        raise ValueError('Scanner rejected a harmless probe.')
    if runtime.scan_document(eicar) is not None:
        raise ValueError('Scanner did not detect the standard test.')


def report(settings, expected_revision, probe_adapters=False):
    checks = []
    observed = None
    def check(name, operation, failure):
        try:
            operation()
        except Exception:
            checks.append(dict(check=name, status='fail', detail=failure))
            return False
        checks.append(dict(check=name, status='pass'))
        return True

    def enabled():
        if os.environ.get('NEXUS_HR_ENABLED') != '1':
            raise ValueError
    def revision():
        nonlocal observed
        observed, clean = release_state()
        if not re.fullmatch(r'[a-f0-9]{40}', expected_revision) or observed != expected_revision or not clean:
            raise ValueError
    def uploads():
        if not runtime.uploads_ready():
            raise ValueError

    check('release', revision, 'Use the expected committed revision with no tracked local changes.')
    check('enabled', enabled, 'Set NEXUS_HR_ENABLED=1 for the selected service.')
    check('signing_key', lambda: hr_signing_key(settings), 'Configure the dedicated HR signing key.')
    check('database_schema', lambda: check_database(settings.database_url),
          'Use an existing absolute SQLite database with the reviewed HR schema; this check never migrates it.')
    check('https_origin', runtime.public_origin, 'Configure the exact HTTPS employee origin.')
    mail_ok = check('mail_configuration', runtime.check_mail, 'Configure the TLS mail adapter (SMTP or Microsoft 365) and sender.')
    files_ok = check('document_configuration', uploads,
                     'Configure the private external directory, encryption keyring and absolute ClamAV socket.')
    for name, configured, operation, failure in [
        ('smtp_authentication', mail_ok, probe_mail, 'TLS SMTP authentication failed; no message was sent.'),
        ('antivirus_detection', files_ok, probe_scanner, 'Scanner transport, harmless acceptance or EICAR detection failed.'),
    ]:
        if probe_adapters and configured:
            check(name, operation, failure)
        else:
            checks.append(dict(check=name, status='not_tested', detail=(
                'Fix configuration before probing.' if not configured else 'Run explicitly with --probe-adapters.')))
    return dict(format_version=1, revision=observed, checks=checks,
                checks_passed=all(c['status'] != 'fail' for c in checks),
                adapter_probes_passed=all(c['status'] == 'pass' for c in checks[-2:]),
                production_ready=False,
                manual_checks_required=[
                    'Running revision, backup restoration, shared DB/document paths and protected service configuration.',
                    'Public HTTPS proxy isolation, request limits and trusted forwarded headers.',
                    'Actual code delivery and full employee journey on a physical phone using synthetic staging data.',
                    'Antivirus signature freshness and approved retention, employer, recipient and payroll owner.',
                ])
