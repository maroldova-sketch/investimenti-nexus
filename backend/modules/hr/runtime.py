"""Explicit optional adapters; no delivery/storage defaults or secret logging."""
import json
import os
import re
import urllib.parse
import urllib.request
import uuid
import socket
import ssl
import smtplib
import struct
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit
from cryptography.fernet import Fernet, MultiFernet

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_ACTIVE_DOCUMENTS = 20
MAX_TOTAL_DOCUMENTS = 50


def public_origin():
    origin = os.environ.get('NEXUS_HR_PUBLIC_ORIGIN', '').rstrip('/')
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('Configure an HTTPS HR origin without a path.')
    return origin


def valid_email(address):
    return bool(address and len(address) <= 254 and re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', address))


def mail_config():
    values = [os.environ.get('NEXUS_HR_SMTP_' + k, '') for k in ['HOST', 'USER', 'PASSWORD', 'FROM']]
    if not all(values) or not valid_email(values[3]) or any(c in values[0] for c in '\r\n'):
        raise ValueError('Configure the HR TLS mail adapter.')
    port = int(os.environ.get('NEXUS_HR_SMTP_PORT', '465'))
    if not 1 <= port <= 65535:
        raise ValueError('Invalid mail port.')
    return (*values, port)


def graph_config():
    """Microsoft 365 sendMail with an app registration (client credentials over verified TLS)."""
    keys = ['TENANT_ID', 'CLIENT_ID', 'CLIENT_SECRET']
    values = [os.environ.get('NEXUS_HR_GRAPH_' + k, '') for k in keys]
    sender = os.environ.get('NEXUS_HR_MAIL_FROM', '')
    if not all(values) or not valid_email(sender) or not re.fullmatch(r'[A-Za-z0-9.-]{1,100}', values[0]):
        raise ValueError('Configure the HR Microsoft 365 mail adapter.')
    return (*values, sender)


def transport():
    return os.environ.get('NEXUS_HR_MAIL_TRANSPORT', 'smtp')


def check_mail():
    if transport() == 'graph':
        return graph_config()
    if transport() == 'smtp':
        return mail_config()
    raise ValueError('Unknown mail transport.')


def invitations_ready():
    try:
        public_origin()
        check_mail()
        return True
    except ValueError:
        return False


def code_message(recipient, code):
    subject = 'Ověření vstupu do personálního formuláře'
    body = (f'Váš jednorázový kód je {code}. Platí 10 minut.\n\n'
            'Pokud jste o vstup nepožádali, kód nikomu nesdělujte.\nNEXUS People')
    return subject, body


def graph_token():
    tenant, client, secret, _ = graph_config()
    data = urllib.parse.urlencode({'client_id': client, 'client_secret': secret, 'grant_type': 'client_credentials',
                                   'scope': 'https://graph.microsoft.com/.default'}).encode()
    request = urllib.request.Request(f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token', data=data,
                                     method='POST')
    with urllib.request.urlopen(request, timeout=15, context=ssl.create_default_context()) as response:
        token = json.loads(response.read(65536)).get('access_token', '')
    if not token:
        raise ValueError('Mail adapter authentication failed.')
    return token


def graph_send(recipient, subject, body):
    """Returns a delivery reference (custom header) so an uncertain send can be traced."""
    _, _, _, sender = graph_config()
    reference = str(uuid.uuid4())
    payload = {'message': {'subject': subject, 'body': {'contentType': 'Text', 'content': body},
                           'toRecipients': [{'emailAddress': {'address': recipient}}],
                           'internetMessageHeaders': [{'name': 'X-Nexus-Hr-Delivery', 'value': reference}]},
               'saveToSentItems': True}
    request = urllib.request.Request(
        f'https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(sender)}/sendMail',
        data=json.dumps(payload).encode(), method='POST',
        headers={'Authorization': 'Bearer ' + graph_token(), 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
        if response.status != 202:
            raise ValueError('Mail adapter did not accept the message.')
    return reference


def send_code(recipient, code):
    if not valid_email(recipient):
        raise ValueError('Invalid recipient.')
    subject, body = code_message(recipient, code)
    if transport() == 'graph':
        return graph_send(recipient, subject, body)
    host, username, password, sender, port = mail_config()
    message = EmailMessage()
    message['From'] = sender
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content(body)
    with smtplib.SMTP_SSL(host, port, timeout=10, context=ssl.create_default_context()) as smtp:
        smtp.login(username, password)
        smtp.send_message(message)
    return None


def document_config():
    raw = os.environ.get('NEXUS_HR_DOCUMENT_ROOT', '')
    root = Path(raw)
    repo = Path(__file__).resolve().parents[3]
    if (not raw or not root.is_absolute() or not root.is_dir() or root.is_symlink()
            or root.resolve().is_relative_to(repo) or root.stat().st_mode & 0o077):
        raise ValueError('Document directory must exist outside the application with private permissions.')
    keys = os.environ.get('NEXUS_HR_DOCUMENT_KEYS', '').split(',')
    cipher = MultiFernet([Fernet(k.strip().encode()) for k in keys])
    return root.resolve(), cipher


def uploads_ready():
    try:
        document_config()
        path = os.environ.get('NEXUS_HR_CLAMD_SOCKET', '')
        return bool(path and Path(path).is_absolute())
    except (ValueError, OSError):
        return False


def clamd_command(command, payload=None):
    path = os.environ.get('NEXUS_HR_CLAMD_SOCKET', '')
    if not path or not Path(path).is_absolute():
        raise ValueError('Configure the private ClamAV Unix socket.')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(path)
        connection.sendall(b'z' + command + b'\0')
        if payload is not None:
            for offset in range(0, len(payload), 65536):
                chunk = payload[offset:offset + 65536]
                connection.sendall(struct.pack('!I', len(chunk)) + chunk)
            connection.sendall(b'\0\0\0\0')
        result = bytearray()
        while b'\0' not in result:
            chunk = connection.recv(512)
            if not chunk or len(result) + len(chunk) > 2048:
                raise ValueError('Incomplete scanner reply.')
            result.extend(chunk)
        return bytes(result).split(b'\0', 1)[0]


def signatures_age_days(version):
    """Age of the loaded signature database from 'ClamAV x.y.z/NNNNN/Sun Nov 16 06:24:00 2026'."""
    from datetime import datetime
    try:
        stamp = version.decode('ascii', errors='replace').split('/', 2)[2].strip()
        built = datetime.strptime(stamp, '%a %b %d %H:%M:%S %Y')
    except (IndexError, ValueError):
        return None
    return (datetime.utcnow() - built).total_seconds() / 86400


def scan_document(data):
    # Files enter durable storage only after an unambiguous successful scan
    # against reasonably fresh signatures (fail closed if updates stopped).
    version = clamd_command(b'VERSION')
    if not version.startswith(b'ClamAV '):
        raise ValueError('Unrecognized scanner.')
    age = signatures_age_days(version)
    if age is None or age > float(os.environ.get('NEXUS_HR_CLAMAV_MAX_AGE_DAYS', '7')):
        raise ValueError('Scanner signatures are missing or stale.')
    result = clamd_command(b'INSTREAM', data)
    if result.endswith(b' FOUND'):
        return None
    if result != b'stream: OK':
        raise ValueError('Scanner did not confirm this file.')
    return version.decode('ascii', errors='replace')[:200]
