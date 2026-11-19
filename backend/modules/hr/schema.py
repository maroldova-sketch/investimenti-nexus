"""Template registry. v1 stays readable and editable under its own validator;
new cases use the current version. Not a payroll calculator or legal certification."""
import re
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from . import schema_v2
from .schema_v2 import AnswerError

V1 = 'cz-existing-2026.11-v1'
YES_NO = [['yes', 'Ano'], ['no', 'Ne'], ['review', 'Potřebuji upřesnit s HR']]


def field(key, label, kind='text', required=False, options=None, when=None, help=None):
    return dict(key=key, label=label, type=kind, required=required,
                options=options, when=when, help=help)


SECTIONS_V1 = [
    {'id': 'personal', 'title': 'Osobní údaje', 'description': 'Zkontrolujte předvyplněné údaje. Oprava se nejprve předá HR.', 'fields': [
        field('first_name', 'Jméno', required=True), field('last_name', 'Příjmení', required=True),
        field('maiden_name', 'Rodné nebo dřívější příjmení'), field('birth_date', 'Datum narození', 'date', True),
        field('birth_place', 'Místo narození'), field('citizenship', 'Občanství', required=True),
        field('address_permanent', 'Adresa trvalého pobytu', 'textarea', True),
        field('personal_id_status', 'České rodné číslo', 'select', True,
              [['assigned', 'Bylo mi přiděleno'], ['not_assigned', 'Nebylo přiděleno'], ['review', 'Upřesním s HR']]),
        field('personal_id', 'Rodné číslo', when={'personal_id_status': ['assigned']}),
        field('foreign_identifier', 'Evidenční číslo pojištěnce, pokud bylo přiděleno', when={'personal_id_status': ['not_assigned']})]},
    {'id': 'contact', 'title': 'Kontakt a výplata', 'description': 'Použije pouze oprávněná personální a mzdová role.', 'fields': [
        field('email', 'Kontaktní e-mail', 'email'), field('phone', 'Telefon', 'tel'),
        field('bank_account', 'Účet pro výplatu / IBAN'), field('health_insurance', 'Zdravotní pojišťovna', required=True),
        field('insurance_status', 'Souběh nebo jiná skutečnost pro zdravotní pojištění', 'textarea', help='Např. další zaměstnání nebo státní kategorie. Neuvádějte diagnózy; rozsah ověří účetní.'),
        field('other_work', 'Další pracovní vztahy', 'textarea', help='Uveďte zaměstnavatele, druh vztahu a období, pokud souvisí s podklady pro mzdy. Nevytváří to novou smlouvu.') ]},
    {'id': 'tax', 'title': 'Daňové podklady', 'description': 'Jde o podklady ke kontrole. Dotazník nenahrazuje podpis Prohlášení poplatníka.', 'fields': [
        field('tax_residency', 'Daňová rezidence', 'select', True, [['CZ', 'Česká republika'], ['other', 'Jiný stát'], ['review', 'Nevím, ověřím s účetní']]),
        field('declaration', 'Chcete zde řešit Prohlášení poplatníka?', 'select', True, YES_NO),
        field('declaration_elsewhere', 'Uplatňujete prohlášení v tomto období u jiného zaměstnavatele?', 'select', True, YES_NO, {'declaration': ['yes']}),
        field('tax_period', 'Období, kterého se žádost týká', 'month', when={'declaration': ['yes']}),
        field('children_claim', 'Chcete řešit daňové zvýhodnění na děti?', 'select', True, YES_NO, {'declaration': ['yes'], 'tax_residency': ['CZ']}),
        field('second_taxpayer', 'Druhý poplatník a způsob doložení uplatnění', 'textarea', when={'children_claim': ['yes'], 'declaration': ['yes'], 'tax_residency': ['CZ']}),
        field('tax_other', 'Další daňové podklady nebo dotaz pro účetní', 'textarea', help='Roční zúčtování a jeho doklady se řeší zvlášť. Nárok se tímto nepřiznává.') ]},
    {'id': 'work', 'title': 'Práce a stávající výhody', 'description': 'Pracovní pozici a vybavení určuje HR. Zde doplňujete existující evidenci.', 'fields': [
        field('qualification', 'Kvalifikace a doklady k pracovní pozici', 'textarea'),
        field('existing_equipment', 'Co už máte převzaté — upřesnění evidence', 'textarea'),
        field('existing_benefits', 'Stávající benefity a karty — upřesnění evidence', 'textarea', help='Nevkládejte PIN ani celé číslo platební karty. Záznam nezakládá nový nárok.'),
        field('note', 'Co potřebujete vysvětlit nebo opravit', 'textarea') ]},
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Child(StrictModel):
    name: str = Field(default='', max_length=200)
    birth_date: str = Field(default='', max_length=10)
    relationship: str = Field(default='', max_length=100)
    household: Literal['', 'yes', 'no', 'review'] = ''
    order: Literal['', '1', '2', '3', 'not_claimed', 'review'] = ''
    months: list[int] = Field(default_factory=list, max_length=12)
    ztpp: Literal['', 'yes', 'no', 'review'] = ''
    study: Literal['', 'yes', 'no', 'review'] = ''


class Requirement(StrictModel):
    id: str = Field(pattern=r'^[a-z0-9_-]{1,40}$')
    label: str = Field(min_length=1, max_length=200)
    owner_role: Literal['hr', 'payroll', 'manager', 'safety', 'employee'] = 'hr'
    verification: Literal['', 'document', 'inspection', 'register', 'statement'] = ''
    blocks_payroll: bool = False
    status: Literal['unknown', 'pending', 'verified', 'not_applicable', 'deferred'] = 'unknown'
    evidence_ref: str = Field(default='', max_length=300)
    reason: str = Field(default='', max_length=500)


def default_requirements_v1():
    return [Requirement(id=k, label=v, owner_role=r).model_dump() for k, v, r in [
        ('contract', 'Pracovní smlouva a případné dodatky', 'hr'),
        ('payroll_docs', 'Podklady požadované mzdovou rolí', 'payroll'),
        ('medical', 'Pracovnělékařská způsobilost podle pozice', 'hr'),
        ('safety', 'BOZP / PO podle pracoviště a činnosti', 'safety'),
        ('equipment', 'Převzetí vybavení a odpovědnosti', 'manager'),
        ('qualification', 'Kvalifikace a platnosti', 'hr')]]


def active(f, answers):
    return all(answers.get(k) in vals for k, vals in (f.get('when') or {}).items())


def children_active(answers):
    return answers.get('children_claim') == 'yes' and answers.get('declaration') == 'yes' and answers.get('tax_residency') == 'CZ'


def normalize_v1(answers, complete=False):
    fields = [f for s in SECTIONS_V1 for f in s['fields']]
    allowed = {f['key'] for f in fields} | {'children'}
    if not isinstance(answers, dict) or set(answers) - allowed:
        raise ValueError('Dotazník obsahuje nepovolená pole.')
    out, errors = {}, {}
    for f in fields:
        k = f['key']
        if not active(f, answers):
            continue
        value = answers.get(k, '')
        if not isinstance(value, str) or len(value) > (2000 if f['type'] == 'textarea' else 300):
            errors[k] = 'Zadejte text v povolené délce.'
            continue
        value = value.strip()
        if f['options'] and value and value not in {o[0] for o in f['options']}:
            errors[k] = 'Vyberte platnou možnost.'
        if value and f['type'] == 'date':
            try:
                if date.fromisoformat(value) > date.today():
                    raise ValueError()
            except ValueError:
                errors[k] = 'Zkontrolujte datum.'
        if value and f['type'] == 'month' and not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value):
            errors[k] = 'Použijte rok a měsíc.'
        if value and f['type'] == 'email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            errors[k] = 'Zkontrolujte e-mail.'
        if complete and f['required'] and not value:
            errors[k] = 'Doplňte údaj nebo zvolte upřesnění s HR.'
        out[k] = value
    if complete and out.get('personal_id_status') == 'assigned' and not out.get('personal_id'):
        errors['personal_id'] = 'Doplňte přidělené rodné číslo.'
    if children_active(out):
        children = answers.get('children', [])
        if not isinstance(children, list) or len(children) > 20:
            raise ValueError('Zkontrolujte seznam dětí.')
        out['children'] = []
        for i, child in enumerate(children):
            row = Child.model_validate(child).model_dump()
            if any(m < 1 or m > 12 for m in row['months']) or len(set(row['months'])) != len(row['months']):
                errors['children'] = 'Měsíce musí být jedinečné hodnoty 1 až 12.'
            if complete and not all(row[k] for k in ['name', 'birth_date', 'relationship', 'household', 'order', 'ztpp', 'study']):
                errors['children'] = f'Doplňte údaje dítěte {i + 1}.'
            if row['birth_date']:
                try:
                    if date.fromisoformat(row['birth_date']) > date.today():
                        raise ValueError()
                except ValueError:
                    errors['children'] = 'Zkontrolujte datum narození dítěte.'
            if complete and row['order'] in ['1', '2', '3'] and not row['months']:
                errors['children'] = 'Vyberte měsíce zamýšleného uplatnění.'
            out['children'].append(row)
        if complete and not out['children']:
            errors['children'] = 'Přidejte dítě nebo změňte volbu zvýhodnění.'
    if errors:
        raise AnswerError(errors)
    return out


def review_issues_v1(answers):
    issues = [f['label'] for s in SECTIONS_V1 for f in s['fields'] if answers.get(f['key']) == 'review']
    if answers.get('declaration') == 'yes' and answers.get('declaration_elsewhere') == 'yes':
        issues.append('Souběh Prohlášení poplatníka — ověřit zaměstnavatele a období.')
    if answers.get('tax_residency') == 'other':
        issues.append('Daňový nerezident — individuální kontrola účetní.')
    if children_active(answers):
        issues.append('Děti — ověřit nároky, období, pořadí a podklady druhého poplatníka.')
    return issues


def v1_ui_sections():
    """v1 children live outside its field list; describe them for the generic renderer."""
    sections = [dict(s, fields=list(s['fields'])) for s in SECTIONS_V1]
    tax = next(s for s in sections if s['id'] == 'tax')
    tax['fields'].append(dict(key='children', label='Děti', type='list', required=False, options=None, help=None,
                              when={'children_claim': ['yes'], 'declaration': ['yes'], 'tax_residency': ['CZ']},
                              items=[dict(key='name', label='Jméno a příjmení', type='text', required=True, options=None, when=None),
                                     dict(key='birth_date', label='Datum narození', type='date', required=True, options=None, when=None),
                                     dict(key='relationship', label='Vztah k dítěti', type='text', required=True, options=None, when=None),
                                     dict(key='household', label='Společná domácnost', type='select', required=True, options=YES_NO, when=None),
                                     dict(key='order', label='Pořadí pro zamýšlené uplatnění', type='select', required=True, when=None,
                                          options=[['1', 'První dítě'], ['2', 'Druhé dítě'], ['3', 'Třetí a další'],
                                                   ['not_claimed', 'Neuplatňuji'], ['review', 'Upřesnit s účetní']]),
                                     dict(key='months', label='Měsíce zamýšleného uplatnění', type='months', required=False, options=None, when=None),
                                     dict(key='ztpp', label='ZTP/P', type='select', required=True, options=YES_NO, when=None),
                                     dict(key='study', label='Doklad o studiu relevantní', type='select', required=True, options=YES_NO, when=None)],
                              add_label='Přidat dítě'))
    return sections


def v1_effective(answers):
    return {k: v for k, v in answers.items() if k != '_review'}


TEMPLATES = {
    V1: dict(version=V1, current=False, review_flags=False, sections=v1_ui_sections(),
             normalize=normalize_v1, issues=review_issues_v1, effective=v1_effective,
             hidden=lambda answers: [], dropped_hidden=lambda previous, new: [],
             defaults=default_requirements_v1, suggested=lambda answers: []),
    schema_v2.VERSION: dict(version=schema_v2.VERSION, current=True, review_flags=True, sections=schema_v2.SECTIONS,
                            normalize=schema_v2.normalize, issues=schema_v2.review_issues,
                            effective=schema_v2.effective, hidden=schema_v2.hidden,
                            dropped_hidden=schema_v2.dropped_hidden,
                            defaults=lambda: [Requirement(id=k, label=v, owner_role=r).model_dump()
                                              for k, v, r in schema_v2.BASE_REQUIREMENTS],
                            suggested=schema_v2.suggested_requirements),
}
VERSION = schema_v2.VERSION
SECTIONS = schema_v2.SECTIONS


def template(version):
    if version not in TEMPLATES:
        raise KeyError(version)
    return TEMPLATES[version]


def normalize(answers, complete=False, version=VERSION):
    return template(version)['normalize'](answers, complete)


def review_issues(answers, version=VERSION):
    return template(version)['issues'](answers)


def default_requirements(version=VERSION):
    return template(version)['defaults']()


def suggested_requirements(answers, existing, version=VERSION):
    present = {x['id'] for x in existing}
    return [Requirement(id=k, label=v, owner_role=r).model_dump()
            for k, v, r in template(version)['suggested'](answers) if k not in present]
