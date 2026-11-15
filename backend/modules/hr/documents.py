"""Bounded intake, antivirus gate, encrypted private storage, scoped downloads."""
import asyncio
import hashlib
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, quote
from uuid import uuid4
from fastapi import HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool
from pydantic import Field, ValidationError
from . import runtime
from .access import HR_ROLES, permitted, check_csrf
from .audit import record
from .models import HRDocument
from .schema import StrictModel


class UploadHeaders(StrictModel):
    expected_version: int = Field(ge=1)
    request_key: str = Field(min_length=16, max_length=100)
    requirement_id: str = Field(pattern=r'^[a-z0-9_-]{1,40}$')
    name: str = Field(min_length=1, max_length=600)


class Withdraw(StrictModel):
    expected_version: int = Field(ge=1)


def manifest(db, case_id, include_withdrawn=False):
    query = db.query(HRDocument).filter_by(case_id=case_id)
    if not include_withdrawn:
        query = query.filter(HRDocument.withdrawn_at.is_(None))
    return [dict(id=d.id, name=d.original_name, media_type=d.media_type, size=d.size,
                 sha256=d.sha256, requirement_id=d.requirement_id,
                 scan_status='clean', created_at=d.created_at.isoformat(),
                 withdrawn=bool(d.withdrawn_at))
            for d in query.order_by(HRDocument.created_at, HRDocument.id).all()]


def validate_reference(db, case_id, reference):
    if reference.startswith('document:'):
        d = db.get(HRDocument, reference.removeprefix('document:'))
        if not d or d.case_id != case_id or d.withdrawn_at:
            raise HTTPException(422, 'Doklad nepatří k tomuto případu nebo byl odebrán.')


def document_path(root, document_id):
    if not re.fullmatch(r'[a-f0-9-]{36}', document_id):
        raise HTTPException(404, 'Doklad nebyl nalezen.')
    path = root / (document_id + '.enc')
    if path.is_symlink():
        raise HTTPException(503, 'Doklad není nyní dostupný.')
    return path


def filename(raw, media_type, data):
    name = unicodedata.normalize('NFC', unquote(raw, errors='strict'))
    if (len(name) > 180 or name in {'.', '..'} or any(c in name for c in '/\\')
            or any(unicodedata.category(c).startswith('C') for c in name)):
        raise HTTPException(422, 'Zvolte krátký název souboru bez lomítek a řídicích znaků.')
    suffix = Path(name).suffix.lower()
    types = {'application/pdf': (['.pdf'], b'%PDF-'),
             'image/jpeg': (['.jpg', '.jpeg'], b'\xff\xd8\xff'),
             'image/png': (['.png'], b'\x89PNG\r\n\x1a\n')}
    if media_type not in types or suffix not in types[media_type][0] or not data.startswith(types[media_type][1]):
        raise HTTPException(415, 'Přiložte PDF, JPG nebo PNG odpovídající skutečnému typu souboru.')
    return name


def may_edit(db, actor, case, employment):
    from .routes import editable
    if employment.person_id != actor.person_id and not permitted(db, actor, employment.entity, HR_ROLES):
        raise HTTPException(403, 'Tato role nepřikládá doklady za zaměstnance.')
    editable(case)


async def upload(case_id, request: Request, actor, db):
    from .routes import resolve, check_version, commit, describe
    check_csrf(request, actor)
    case, employment = resolve(db, actor, case_id)
    may_edit(db, actor, case, employment)
    try:
        body = UploadHeaders(expected_version=request.headers.get('x-hr-expected-version'),
                             request_key=request.headers.get('x-hr-request-key'),
                             requirement_id=request.headers.get('x-hr-requirement'),
                             name=request.headers.get('x-hr-file-name'))
    except ValidationError:
        raise HTTPException(422, 'Chybí metadata souboru. Zkuste jej přiložit znovu.')
    if not runtime.uploads_ready():
        raise HTTPException(503, 'Příjem dokladů ještě není nakonfigurovaný. Kontaktujte HR.')
    root, cipher = runtime.document_config()
    try:
        length = int(request.headers.get('content-length', '0'))
    except ValueError:
        raise HTTPException(400, 'Neplatná velikost souboru.')
    if length < 0 or length > runtime.MAX_DOCUMENT_BYTES:
        raise HTTPException(413, 'Jeden doklad může mít nejvýše 8 MB.')
    chunks = bytearray()
    try:
        async with asyncio.timeout(30):
            async for chunk in request.stream():
                if len(chunks) + len(chunk) > runtime.MAX_DOCUMENT_BYTES:
                    raise HTTPException(413, 'Jeden doklad může mít nejvýše 8 MB.')
                chunks.extend(chunk)
    except TimeoutError:
        raise HTTPException(408, 'Nahrávání trvalo příliš dlouho. Zkuste to znovu.')
    data = bytes(chunks)
    if not data:
        raise HTTPException(422, 'Soubor je prázdný.')
    media_type = request.headers.get('content-type', '').split(';', 1)[0].lower()
    name = filename(body.name, media_type, data)
    digest = hashlib.sha256(data).hexdigest()
    previous = db.query(HRDocument).filter_by(case_id=case.id, request_key=body.request_key).first()
    if previous:
        if (previous.sha256, previous.original_name, previous.requirement_id, previous.uploaded_by) != (digest, name, body.requirement_id, actor.id):
            raise HTTPException(409, 'Klíč nahrávání byl použit pro jiný doklad.')
        return describe(db, actor, case, employment, True)
    check_version(case, body.expected_version)
    if body.requirement_id not in [x['id'] for x in case.requirements]:
        raise HTTPException(422, 'Vyberte požadavek, ke kterému doklad patří.')
    all_docs = db.query(HRDocument).filter_by(case_id=case.id).all()
    if len(all_docs) >= runtime.MAX_TOTAL_DOCUMENTS or sum(not x.withdrawn_at for x in all_docs) >= runtime.MAX_ACTIVE_DOCUMENTS:
        raise HTTPException(409, 'Počet dokladů dosáhl limitu. Další postup domluvte s HR.')
    try:
        receipt = await run_in_threadpool(runtime.scan_document, data)
    except (OSError, ValueError):
        raise HTTPException(503, 'Kontrola souboru není dostupná. Doklad nebyl přijat; zkuste to později.')
    if not receipt:
        raise HTTPException(422, 'Kontrola soubor odmítla. Použijte nový bezpečný export dokumentu.')
    # A slow upload/scan must not bypass a concurrent submission or revocation.
    db.expire_all()
    case, employment = resolve(db, actor, case_id)
    may_edit(db, actor, case, employment)
    check_version(case, body.expected_version)
    document_id = str(uuid4())
    path = document_path(root, document_id)
    committing = False
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as target:
            target.write(cipher.encrypt(data))
            target.flush()
            os.fsync(target.fileno())
        directory_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        db.add(HRDocument(id=document_id, case_id=case.id, request_key=body.request_key,
                          original_name=name, media_type=media_type, size=len(data), sha256=digest,
                          requirement_id=body.requirement_id, uploaded_by=actor.id, scan_receipt=receipt))
        case.version += 1
        record(db, case.id, 'document_uploaded', actor, document_id=document_id)
        committing = True
        commit(db)
    except Exception as exc:
        db.rollback()
        # A known optimistic conflict did not commit. An unknown DB failure may
        # have committed remotely: retain ciphertext for reconciliation instead
        # of deleting a possibly referenced document.
        if not committing or isinstance(exc, HTTPException) and exc.status_code == 409:
            path.unlink(missing_ok=True)
        raise
    return describe(db, actor, case, employment, True)


def download(case_id, document_id, actor, db):
    from .routes import resolve, commit
    case, _ = resolve(db, actor, case_id)
    doc = db.get(HRDocument, document_id)
    if not doc or doc.case_id != case.id:
        raise HTTPException(404, 'Doklad nebyl nalezen.')
    try:
        root, cipher = runtime.document_config()
        path = document_path(root, doc.id)
        if path.stat().st_size > runtime.MAX_DOCUMENT_BYTES * 2:
            raise ValueError('Stored file too large.')
        data = cipher.decrypt(path.read_bytes())
        if len(data) != doc.size or hashlib.sha256(data).hexdigest() != doc.sha256:
            raise ValueError('Document integrity check failed.')
    except Exception:
        raise HTTPException(503, 'Doklad není nyní dostupný. Kontaktujte HR.')
    record(db, case.id, 'document_downloaded', actor, document_id=doc.id)
    commit(db)
    return Response(data, media_type=doc.media_type,
                    headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                             'Content-Security-Policy': "sandbox; default-src 'none'",
                             'Content-Disposition': "attachment; filename*=UTF-8''" + quote(doc.original_name, safe='')})


def withdraw(case_id, document_id, body: Withdraw, request, actor, db):
    from .routes import resolve, check_version, commit, describe
    check_csrf(request, actor)
    case, employment = resolve(db, actor, case_id)
    may_edit(db, actor, case, employment)
    doc = db.get(HRDocument, document_id)
    if not doc or doc.case_id != case.id:
        raise HTTPException(404, 'Doklad nebyl nalezen.')
    if doc.withdrawn_at:
        return describe(db, actor, case, employment, True)
    check_version(case, body.expected_version)
    if any(x.get('evidence_ref') == 'document:' + doc.id for x in case.requirements):
        raise HTTPException(409, 'HR nejprve musí upravit požadavek odkazující na tento doklad.')
    doc.withdrawn_at = datetime.now(timezone.utc).replace(tzinfo=None)
    case.version += 1
    record(db, case.id, 'document_withdrawn', actor, document_id=doc.id)
    commit(db)
    return describe(db, actor, case, employment, True)
