"""Explicit optional adapters; no delivery/storage defaults or secret logging."""
import os
import re
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


def invitations_ready():
    try:
        public_origin()
        mail_config()
        return True
    except ValueError:
        return False


def send_code(recipient, code):
    host, username, password, sender, port = mail_config()
    if not valid_email(recipient):
        raise ValueError('Invalid recipient.')
    message = EmailMessage()
    message['From'] = sender
    message['To'] = recipient
    message['Subject'] = 'Ověření vstupu do personálního formuláře'
    message.set_content(f'Váš jednorázový kód je {code}. Platí 10 minut.\n\n'
                        'Pokud jste o vstup nepožádali, kód nikomu nesdělujte.\nNEXUS People')
    with smtplib.SMTP_SSL(host, port, timeout=10, context=ssl.create_default_context()) as smtp:
        smtp.login(username, password)
        smtp.send_message(message)


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


def scan_document(data):
    # Files enter durable storage only after an unambiguous successful scan.
    version = clamd_command(b'VERSION')
    if not version.startswith(b'ClamAV '):
        raise ValueError('Unrecognized scanner.')
    result = clamd_command(b'INSTREAM', data)
    if result.endswith(b' FOUND'):
        return None
    if result != b'stream: OK':
        raise ValueError('Scanner did not confirm this file.')
    return version.decode('ascii', errors='replace')[:200]
