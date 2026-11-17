"""Structured export of one reviewed revision for the HR / payroll role.

This is a neutral, documented format (JSON + CSV + XLSX + document manifest +
unresolved items). It is NOT a POHODA or PAMICA import file. Payroll receipt,
a successful import into payroll software and an official filing are three
separately confirmed decisions; an export download confirms none of them.
"""
import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.security.auth import get_current_user
from .access import HR_ROLES, PAYROLL_ROLES, permitted, value
from .audit import record
from .models import HRDecision, HRSubmission
from .schema import template
from .terms import latest_terms

router = APIRouter(tags=['hr-export'])
EXPORT_SCHEMA = 'nexus-hr-export/1'
NOTICE = ('Neutrální strukturovaný export schválené revize. Nejde o importní soubor POHODA ani PAMICA. '
          'Převzetí mzdovou rolí, úspěšný import do mzdového programu a úřední podání se potvrzují samostatně.')


def label_of(spec, raw):
    for key, label in spec.get('options') or []:
        if key == raw:
            return label
    return ''


def rows_for(sections, answers, review, revision):
    rows = []
    for section in sections:
        for spec in section['fields']:
            key = spec['key']
            if key not in answers:
                continue
            raw = answers[key]
            if spec['type'] == 'list':
                for i, item in enumerate(raw or []):
                    for sub in spec.get('items', []):
                        val = item.get(sub['key'], '')
                        if isinstance(val, list):
                            val = ','.join(str(v) for v in val)
                        rows.append(dict(section=section['id'], key=f'{key}[{i}].{sub["key"]}',
                                         label=f'{spec["label"]} {i + 1}: {sub["label"]}', value=str(val),
                                         value_label=label_of(sub, val),
                                         status='review' if val == 'review' else ('provided' if val else 'empty'),
                                         source='employee_submission', revision=revision))
                continue
            status = 'review' if raw == 'review' or key in review else ('provided' if raw else 'empty')
            rows.append(dict(section=section['id'], key=key, label=spec['label'], value=str(raw),
                             value_label=label_of(spec, raw), status=status,
                             source='employee_submission', revision=revision))
    return rows


def build(db, case, employment, actor):
    if case.status not in ['reviewed', 'payroll_received'] or not case.current_revision:
        raise HTTPException(409, 'Exportovat lze jen revizi zkontrolovanou HR.')
    revision = case.current_revision
    submission = db.query(HRSubmission).filter_by(case_id=case.id, revision=revision).first()
    decisions = db.query(HRDecision).filter_by(case_id=case.id).order_by(HRDecision.created_at).all()
    reviewed = [d for d in decisions if d.action == 'review' and d.revision == revision]
    if not submission or not reviewed:
        raise HTTPException(409, 'Chybí zkontrolovaná revize podání.')
    snapshot = submission.snapshot
    answers = snapshot.get('answers', {})
    try:
        tpl = template(snapshot.get('template_version', case.template_version))
        sections = tpl['sections']
        issues = snapshot.get('issues') if 'issues' in snapshot else tpl['issues'](answers)
    except KeyError:
        sections, issues = [], ['Neznámá verze šablony — export obsahuje jen surové odpovědi.']
    review = set(answers.get('_review', []))
    terms = latest_terms(db, employment.id)
    requirements = reviewed[-1].evidence.get('requirements', case.requirements)
    unresolved = [dict(kind='answer', text=t) for t in issues]
    unresolved += [dict(kind='requirement', id=r['id'], text=r['label'], status=r['status'], owner_role=r['owner_role'])
                   for r in requirements if r['status'] not in ['verified', 'not_applicable']]
    person, entity = employment.person, employment.entity
    data = dict(
        export_schema=EXPORT_SCHEMA, notice=NOTICE,
        generated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'), generated_by=actor.id,
        person=dict(person_id=person.id, name=person.full_name),
        employer=dict(entity_id=entity.id, legal_name=entity.legal_name or entity.name, ico=entity.ico or ''),
        employment=dict(employment_id=employment.id, type=value(employment.employment_type),
                        status=value(employment.status), position=employment.position or '',
                        date_start=employment.date_start or '', date_end=employment.date_end or ''),
        case=dict(case_id=case.id, kind=case.kind, status=case.status,
                  template_version=snapshot.get('template_version', case.template_version),
                  revision=revision, submission_sha256=submission.sha256,
                  submitted_at=submission.created_at.isoformat() + 'Z',
                  reviewed_at=reviewed[-1].created_at.isoformat() + 'Z', reviewed_by=reviewed[-1].actor_id),
        effective_from=(terms or {}).get('effective_from') or employment.date_start or '',
        fields=rows_for(sections, answers, review, revision),
        hr_terms=dict(terms, source_kind='hr_internal') if terms else None,
        documents=[dict(d, requirement_label=next((r['label'] for r in requirements if r['id'] == d['requirement_id']), ''))
                   for d in snapshot.get('documents', [])],
        requirements=requirements, unresolved=unresolved,
        decisions=[dict(action=d.action, revision=d.revision, at=d.created_at.isoformat() + 'Z',
                        actor_id=d.actor_id, note=d.note) for d in decisions],
        confirmations=dict(
            payroll_received=any(d.action == 'payroll_receive' and d.revision == revision for d in decisions),
            payroll_imported=any(d.action == 'payroll_import' and d.revision == revision for d in decisions),
            authority_filed=any(d.action == 'authority_filing' and d.revision == revision for d in decisions)))
    return data


def as_csv(rows, columns):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, quoting=csv.QUOTE_ALL, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return ('﻿' + out.getvalue()).encode('utf-8')


def as_xlsx(data):
    from openpyxl import Workbook
    book = Workbook()
    def sheet(title, columns, rows):
        ws = book.create_sheet(title)
        ws.append(columns)
        for row in rows:
            ws.append([str(row.get(c, '')) for c in columns])
        for column in ws.iter_cols(min_row=2):
            for cell in column:
                cell.number_format = '@'  # identifiers stay text (leading zeros, slashes)
    info = book.active
    info.title = 'Případ'
    for key, val in [('export_schema', data['export_schema']), ('upozornění', data['notice']),
                     ('person_id', data['person']['person_id']), ('jméno', data['person']['name']),
                     ('zaměstnavatel', data['employer']['legal_name']), ('IČO', data['employer']['ico']),
                     ('employment_id', data['employment']['employment_id']), ('druh vztahu', data['employment']['type']),
                     ('case_id', data['case']['case_id']), ('šablona', data['case']['template_version']),
                     ('revize', data['case']['revision']), ('SHA-256 podání', data['case']['submission_sha256']),
                     ('účinnost od', data['effective_from'])]:
        info.append([key, str(val)])
    for row in info.iter_rows():
        row[1].number_format = '@'
    sheet('Údaje', FIELD_COLUMNS, data['fields'])
    sheet('Doklady', DOC_COLUMNS, data['documents'])
    sheet('Nevyřešené', UNRESOLVED_COLUMNS, data['unresolved'])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


FIELD_COLUMNS = ['section', 'key', 'label', 'value', 'value_label', 'status', 'source', 'revision']
DOC_COLUMNS = ['id', 'requirement_id', 'requirement_label', 'name', 'media_type', 'size', 'sha256', 'scan_status', 'created_at']
UNRESOLVED_COLUMNS = ['kind', 'id', 'text', 'status', 'owner_role']


@router.get('/api/hr/cases/{case_id}/export')
def export(case_id: str, fmt: Literal['json', 'csv', 'xlsx', 'zip'] = 'zip',
           cu=Depends(get_current_user), db: Session = Depends(get_db)):
    from .routes import resolve, commit
    case, employment = resolve(db, cu, case_id)
    if not permitted(db, cu, employment.entity, HR_ROLES | PAYROLL_ROLES) or getattr(cu, 'portal', False):
        raise HTTPException(403, 'Export je určen pověřené personální nebo mzdové roli.')
    data = build(db, case, employment, cu)
    stem = f'nexus-hr-{case.id[:8]}-r{data["case"]["revision"]}'
    payload_json = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    if fmt == 'json':
        body, media, name = payload_json, 'application/json', stem + '.json'
    elif fmt == 'csv':
        body, media, name = as_csv(data['fields'], FIELD_COLUMNS), 'text/csv; charset=utf-8', stem + '.csv'
    elif fmt == 'xlsx':
        body = as_xlsx(data)
        media, name = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', stem + '.xlsx'
    else:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('export.json', payload_json)
            archive.writestr('udaje.csv', as_csv(data['fields'], FIELD_COLUMNS))
            archive.writestr('export.xlsx', as_xlsx(data))
            archive.writestr('doklady_manifest.json', json.dumps(data['documents'], ensure_ascii=False, indent=2))
            archive.writestr('nevyresene.csv', as_csv(data['unresolved'], UNRESOLVED_COLUMNS))
            archive.writestr('CTI_ME.txt', NOTICE + '\n')
        body, media, name = buffer.getvalue(), 'application/zip', stem + '.zip'
    record(db, case.id, 'export_created', cu, revision=data['case']['revision'], format=fmt,
           sha256=hashlib.sha256(body).hexdigest())
    commit(db)
    return Response(body, media_type=media, headers={'Content-Disposition': f'attachment; filename="{name}"',
                                                     'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
