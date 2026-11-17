"""Intake template v2: frozen field set, conditional branches, review flags.

It is a structured collection of payroll inputs, not a legal or tax validator.
Hidden branch answers stay in the draft until an explicit confirmed clearing;
only active answers become part of an immutable submission.
"""
import re
from datetime import date, timedelta

VERSION = 'cz-existing-2026.11-v2'
REVIEW = ['review', 'Potřebuji upřesnit s HR']
YES_NO = [['yes', 'Ano'], ['no', 'Ne'], REVIEW]
CZ_COUNTRY = {'cz', 'cze', 'česko', 'cesko', 'česká republika', 'ceska republika', 'czechia', 'czech republic'}
FOREIGN = ['eu', 'third', 'review']
TEXT_LIMIT, AREA_LIMIT, MAX_LIST = 300, 2000, 20


def f(key, label, kind='text', required=False, options=None, when=None, help=None, check=None, **extra):
    return dict(key=key, label=label, type=kind, required=required, options=options,
                when=when, help=help, check=check, **extra)


def address(prefix, title, when=None, required=True):
    return [f(prefix + '_street', f'{title}: ulice nebo část obce', required=required, when=when),
            f(prefix + '_number', f'{title}: číslo popisné / orientační', required=required, when=when),
            f(prefix + '_city', f'{title}: obec', required=required, when=when),
            f(prefix + '_zip', f'{title}: PSČ', required=required, when=when, check='zip:' + prefix),
            f(prefix + '_country', f'{title}: stát', required=required, when=when,
              help='Např. Česká republika.')]


CHILD_FIELDS = [
    f('name', 'Jméno a příjmení dítěte', required=True),
    f('birth_date', 'Datum narození', 'date', True, check='past'),
    f('personal_id_status', 'Rodné číslo dítěte', 'select', True,
      [['assigned', 'Bylo přiděleno'], ['not_assigned', 'Nebylo přiděleno'], REVIEW]),
    f('personal_id', 'Rodné číslo dítěte', when={'personal_id_status': ['assigned']}, required=True, check='rc'),
    f('relationship', 'Vztah k dítěti', 'select', True,
      [['own', 'Vlastní nebo osvojené dítě'], ['partner', 'Dítě manžela/manželky nebo partnera'],
       ['foster', 'Dítě v péči nahrazující péči rodičů'], ['grandchild', 'Vnuk nebo vnučka'], REVIEW]),
    f('household', 'Žije se mnou ve společné domácnosti', 'select', True, YES_NO),
    f('order', 'Pořadí pro zamýšlené uplatnění', 'select', True,
      [['1', 'První dítě'], ['2', 'Druhé dítě'], ['3', 'Třetí a další dítě'],
       ['not_claimed', 'Na toto dítě zvýhodnění neuplatňuji'], REVIEW]),
    f('months', 'Měsíce zamýšleného uplatnění', 'months'),
    f('ztpp', 'Dítě je držitelem průkazu ZTP/P', 'select', True, YES_NO),
    f('study', 'Soustavná příprava na povolání (dítě starší 18 let)', 'select', False, YES_NO),
]

JOB_FIELDS = [
    f('employer', 'Zaměstnavatel nebo jiný plátce', required=True),
    f('kind', 'Druh vztahu nebo příjmu', 'select', True,
      [['HPP', 'Pracovní poměr'], ['DPP', 'Dohoda o provedení práce'], ['DPC', 'Dohoda o pracovní činnosti'],
       ['OSVC', 'Samostatná výdělečná činnost'], ['other', 'Jiný příjem'], REVIEW]),
    f('date_from', 'Od', 'date', True, check='any'),
    f('date_to', 'Do (prázdné = trvá)', 'date', check='any'),
    f('insured', 'Zakládá účast na pojištění', 'select', False, YES_NO),
    f('note', 'Poznámka pro mzdovou účetní'),
]

SECTIONS = [
    {'id': 'identity', 'title': 'Osobní údaje',
     'description': 'Zkontrolujte předvyplněné údaje. Opravu nejprve posoudí HR; dotazník sám nic nepřepisuje v osobní kartě.',
     'fields': [
         f('title_before', 'Titul před jménem'),
         f('first_name', 'Jméno', required=True), f('last_name', 'Příjmení', required=True),
         f('maiden_name', 'Rodné příjmení, pokud se liší'),
         f('birth_date', 'Datum narození', 'date', True, check='past'),
         f('birth_place', 'Místo narození (obec)', required=True),
         f('birth_country', 'Stát narození', required=True),
         f('citizenship', 'Státní občanství', required=True, help='Jde o státní občanství, ne o národnost.'),
         f('citizenship_group', 'Občanství pro účely zaměstnání', 'select', True,
           [['cz', 'Česká republika'], ['eu', 'Jiný stát EU/EHP nebo Švýcarsko'], ['third', 'Jiný stát'], REVIEW]),
         f('personal_id_status', 'České rodné číslo', 'select', True,
           [['assigned', 'Bylo mi přiděleno'], ['not_assigned', 'Nebylo mi přiděleno'], REVIEW]),
         f('personal_id', 'Rodné číslo', when={'personal_id_status': ['assigned']}, required=True, check='rc'),
         f('sex', 'Pohlaví (pro registraci bez rodného čísla)', 'select', True,
           [['F', 'Žena'], ['M', 'Muž']], when={'personal_id_status': ['not_assigned']}),
     ]},
    {'id': 'address', 'title': 'Adresy',
     'description': 'Adresu uvádějte po částech, aby ji mzdová účetní nemusela přepisovat.',
     'fields': [
         *address('perm', 'Trvalý pobyt'),
         f('contact_same', 'Doručovací adresa je stejná jako trvalý pobyt', 'select', True,
           [['yes', 'Ano'], ['no', 'Ne, uvedu jinou']]),
         *address('contact', 'Doručovací adresa', {'contact_same': ['no']}),
     ]},
    {'id': 'contact', 'title': 'Kontakt a výplata',
     'description': 'Použije pouze oprávněná personální a mzdová role.',
     'fields': [
         f('email', 'Soukromý e-mail pro mzdové informace', 'email',
           help='Přístupový kód do formuláře chodí na kontakt ověřený HR; tato změna ho nemění.'),
         f('phone', 'Telefon', 'tel'),
         f('payment_method', 'Výplata mzdy', 'select', True,
           [['bank', 'Na bankovní účet'], ['cash', 'Hotově (jen po dohodě s HR)'], REVIEW]),
         f('bank_account', 'Číslo účtu nebo IBAN', when={'payment_method': ['bank']}, required=True, check='account',
           help='Např. 19-123457/0800 nebo IBAN.'),
         f('account_holder', 'Majitel účtu', 'select', True,
           [['own', 'Vlastní účet'], ['other', 'Účet jiné osoby'], REVIEW], when={'payment_method': ['bank']}),
         f('account_holder_name', 'Jméno majitele účtu', when={'account_holder': ['other']}, required=True,
           help='Výplata na účet jiné osoby vyžaduje vaši písemnou žádost; HR ji ověří.'),
     ]},
    {'id': 'insurance', 'title': 'Pojištění a důchod',
     'description': 'Pojistné identifikátory a statusy. Neuvádějte diagnózy ani zdravotní údaje.',
     'fields': [
         f('health_insurer', 'Zdravotní pojišťovna', 'select', True,
           [['111', '111 VZP'], ['201', '201 VoZP'], ['205', '205 ČPZP'], ['207', '207 OZP'],
            ['209', '209 ZPŠ'], ['211', '211 ZPMV'], ['213', '213 RBP'],
            ['foreign', 'Pojištění v jiném státě'], REVIEW]),
         f('health_insured_number', 'Číslo pojištěnce u zdravotní pojišťovny',
           when={'personal_id_status': ['not_assigned', 'review']},
           help='Má-li pojištěnec rodné číslo, bývá jím zpravidla rodné číslo.'),
         f('cssz_number', 'Evidenční číslo pojištěnce ČSSZ (EČP)',
           when={'personal_id_status': ['not_assigned', 'review']}, help='Pokud bylo přiděleno.'),
         f('foreign_social_security', 'Jsem sociálně pojištěn(a) v jiném státě (formulář A1)', 'select', True,
           YES_NO, when={'citizenship_group': FOREIGN}),
         f('state_insured', 'Platí za mě pojistné i stát (např. student, poživatel důchodu, rodič malého dítěte)',
           'select', True, YES_NO),
         f('state_insured_category', 'Kategorie státního pojištěnce', 'select', True,
           [['student', 'Nezaopatřené dítě / student'], ['pension', 'Poživatel důchodu'],
            ['parent', 'Rodičovská nebo péče o dítě do 7 let'], ['other', 'Jiná kategorie'], REVIEW],
           when={'state_insured': ['yes']}),
         f('pension_status', 'Pobírám důchod', 'select', True,
           [['none', 'Nepobírám'], ['old_age', 'Starobní důchod'], ['disability_12', 'Invalidní důchod I. nebo II. stupně'],
            ['disability_3', 'Invalidní důchod III. stupně'], ['other', 'Jiný důchod (např. vdovský, sirotčí)'], REVIEW]),
         f('pension_from', 'Důchod pobírám od', 'date', True, check='past',
           when={'pension_status': ['old_age', 'disability_12', 'disability_3', 'other']}),
     ]},
    {'id': 'other_work', 'title': 'Další zaměstnání',
     'description': 'Souběhy ovlivňují pojištění i Prohlášení poplatníka. Nevzniká tím žádná nová smlouva.',
     'fields': [
         f('other_employment', 'Mám souběžně jiné zaměstnání, dohodu nebo podnikám', 'select', True, YES_NO),
         f('other_jobs', 'Další vztahy a období', 'list', when={'other_employment': ['yes']},
           items=JOB_FIELDS, min_items=1, add_label='Přidat další vztah'),
         f('declaration_elsewhere_status', 'Prohlášení poplatníka u jiného plátce', 'select', True,
           [['signed_elsewhere', 'Mám ho podepsané u jiného plátce'], ['not_signed', 'Jinde podepsané nemám'], REVIEW],
           when={'other_employment': ['yes', 'review']}),
         f('declaration_elsewhere_period', 'Od kdy a u koho je jinde podepsané', when={'declaration_elsewhere_status': ['signed_elsewhere']}),
     ]},
    {'id': 'tax', 'title': 'Daně a děti',
     'description': 'Jde o podklady ke kontrole. Dotazník nenahrazuje podpis Prohlášení poplatníka a nárok nepřiznává.',
     'fields': [
         f('tax_residency', 'Daňová rezidence', 'select', True,
           [['CZ', 'Česká republika'], ['other', 'Jiný stát'], REVIEW]),
         f('tax_residence_country', 'Stát daňové rezidence', when={'tax_residency': ['other']}, required=True),
         f('foreign_tax_id', 'Daňové identifikační číslo ve státě rezidence', when={'tax_residency': ['other']}),
         f('declaration', 'Chci u tohoto zaměstnavatele podepsat Prohlášení poplatníka', 'select', True, YES_NO),
         f('tax_period', 'Od kterého měsíce', 'month', True, when={'declaration': ['yes']}),
         f('ztpp_holder', 'Jsem držitelem průkazu ZTP/P', 'select', True, YES_NO, when={'declaration': ['yes']}),
         f('children_claim', 'Chci uplatnit daňové zvýhodnění na vyživované dítě', 'select', True, YES_NO,
           when={'declaration': ['yes']}),
         f('children', 'Děti', 'list', when={'children_claim': ['yes']}, items=CHILD_FIELDS, min_items=1,
           add_label='Přidat dítě'),
         f('second_taxpayer', 'Druhý z rodičů / poplatníků v domácnosti', 'select', True,
           [['claims', 'Zvýhodnění také uplatňuje (na jiné dítě nebo jiné měsíce)'],
            ['not_claims', 'Zvýhodnění neuplatňuje'], ['none', 'Druhý poplatník v domácnosti není'], REVIEW],
           when={'children_claim': ['yes']}),
         f('second_taxpayer_name', 'Jméno a příjmení druhého poplatníka', required=True,
           when={'second_taxpayer': ['claims', 'not_claims']}),
         f('second_taxpayer_personal_id', 'Rodné číslo druhého poplatníka', check='rc',
           when={'second_taxpayer': ['claims', 'not_claims']}),
         f('second_taxpayer_employer', 'Zaměstnavatel druhého poplatníka a jeho adresa', 'textarea',
           when={'second_taxpayer': ['claims', 'not_claims']}),
         f('tax_other', 'Další daňový dotaz pro účetní', 'textarea',
           help='Roční zúčtování a jeho doklady se řeší zvlášť.'),
     ]},
    {'id': 'deductions', 'title': 'Srážky ze mzdy',
     'description': 'Exekuce, insolvence a dobrovolné srážky vedeme odděleně. Výpočet a pořadí určuje mzdová účetní.',
     'fields': [
         f('enforcement', 'Mám nařízenou exekuci, výživné nebo jinou srážku soudem či úřadem', 'select', True, YES_NO),
         f('enforcement_detail', 'Kdo srážku nařídil a číslo jednací', 'textarea', when={'enforcement': ['yes']}),
         f('insolvency', 'Probíhá u mě insolvence nebo oddlužení', 'select', True, YES_NO),
         f('insolvency_detail', 'Spisová značka insolvenčního řízení', when={'insolvency': ['yes']}),
         f('voluntary_deductions', 'Chci sjednat dobrovolnou srážku (např. penzijní spoření, splátka)', 'select', True, YES_NO),
         f('voluntary_detail', 'Jakou dobrovolnou srážku', 'textarea', when={'voluntary_deductions': ['yes']}),
     ]},
    {'id': 'foreign', 'title': 'Pobyt a oprávnění k práci',
     'description': 'Jen pro občany jiného státu. Kopii dokladu nepřikládejte, pokud ji HR výslovně nevyžádá.',
     'when': {'citizenship_group': FOREIGN},
     'fields': [
         f('id_doc_type', 'Doklad totožnosti', 'select', True,
           [['passport', 'Cestovní pas'], ['eu_id', 'Průkaz totožnosti státu EU'], ['residence_card', 'Průkaz o pobytu'], REVIEW],
           when={'citizenship_group': FOREIGN}),
         f('id_doc_number', 'Číslo dokladu', required=True, when={'citizenship_group': FOREIGN}),
         f('id_doc_valid_to', 'Doklad platí do', 'date', True, check='any', when={'citizenship_group': FOREIGN}),
         f('abroad_address', 'Adresa bydliště v cizině, pokud se liší', 'textarea', when={'citizenship_group': FOREIGN}),
         f('residence_permit', 'Pobytové oprávnění', 'select', True,
           [['employee_card', 'Zaměstnanecká karta'], ['blue_card', 'Modrá karta'], ['long_term', 'Dlouhodobý pobyt'],
            ['permanent', 'Trvalý pobyt'], ['temporary_protection', 'Dočasná ochrana'],
            ['family', 'Pobyt rodinného příslušníka'], ['other', 'Jiné'], REVIEW],
           when={'citizenship_group': ['third', 'review']}),
         f('residence_permit_number', 'Číslo pobytového oprávnění', when={'citizenship_group': ['third', 'review']}),
         f('residence_valid_from', 'Pobyt platí od', 'date', check='any', when={'citizenship_group': ['third', 'review']}),
         f('residence_valid_to', 'Pobyt platí do', 'date', check='any',
           when={'residence_permit': ['employee_card', 'blue_card', 'long_term', 'temporary_protection', 'family', 'other']}),
         f('free_access', 'Mám volný přístup na trh práce', 'select', True, YES_NO,
           when={'citizenship_group': ['third', 'review']}),
         f('work_permit_valid_to', 'Povolení k zaměstnání platí do', 'date', True, check='any',
           when={'free_access': ['no']}),
     ]},
    {'id': 'work', 'title': 'Kvalifikace a stávající předání',
     'description': 'Pozici, vybavení a benefity určuje HR. Zde jen upřesníte, co už máte; nic se tím neobjednává.',
     'fields': [
         f('qualification', 'Vzdělání a doklady potřebné pro pozici', 'textarea',
           help='Např. řidičský průkaz, hygienické minimum, odborná způsobilost.'),
         f('existing_equipment_note', 'Upřesnění k převzatému vybavení', 'textarea'),
         f('existing_benefits_note', 'Upřesnění ke stávajícím benefitům a kartám', 'textarea',
           help='Nevkládejte PIN ani celé číslo platební karty.'),
         f('note', 'Co potřebujete vysvětlit nebo opravit', 'textarea'),
     ]},
]

FIELDS = [x for s in SECTIONS for x in s['fields']]
BY_KEY = {x['key']: x for x in FIELDS}


class AnswerError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('Zkontrolujte označené údaje.')


def valid_rc(value):
    s = value.replace('/', '').replace(' ', '')
    if not re.fullmatch(r'\d{9,10}', s):
        return False
    month, day = int(s[2:4]), int(s[4:6])
    if not (1 <= month % 50 <= 12 or 21 <= month % 50 <= 32) or not 1 <= day <= 31:
        return False
    if len(s) == 9:
        return int(s[:2]) < 54
    number = int(s)
    return number % 11 == 0 or (int(s[:9]) % 11 == 10 and s[9] == '0')


def valid_account(value):
    compact = value.replace(' ', '').upper()
    if re.fullmatch(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', compact):
        moved = compact[4:] + compact[:4]
        return int(''.join(str(int(c, 36)) for c in moved)) % 97 == 1
    match = re.fullmatch(r'(?:(\d{1,6})-)?(\d{2,10})/(\d{4})', compact)
    if not match:
        return False
    def weighted(digits, weights):
        digits = digits.zfill(len(weights))
        return sum(int(d) * w for d, w in zip(digits, weights)) % 11 == 0
    prefix, number = match.group(1) or '', match.group(2)
    return weighted(prefix, [10, 5, 8, 4, 2, 1]) and weighted(number, [6, 3, 7, 9, 10, 5, 8, 4, 2, 1])


def czech(country):
    return (country or '').strip().lower() in CZ_COUNTRY


def check_value(spec, value, answers, item=None):
    kind, check = spec['type'], spec.get('check') or ''
    if spec['options'] and value not in {o[0] for o in spec['options']}:
        return 'Vyberte platnou možnost.'
    if kind == 'date':
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return 'Zkontrolujte datum.'
        if check == 'past' and parsed > date.today():
            return 'Datum nemůže být v budoucnosti.'
        if parsed.year < 1900 or parsed.year > 2100:
            return 'Zkontrolujte rok.'
    if kind == 'month' and not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value):
        return 'Použijte rok a měsíc.'
    if kind == 'email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        return 'Zkontrolujte e-mail.'
    if kind == 'tel' and not re.fullmatch(r'\+?[0-9 ()-]{6,20}', value):
        return 'Zkontrolujte telefon.'
    if check == 'rc' and not valid_rc(value):
        return 'Zkontrolujte rodné číslo, nebo zvolte upřesnění s HR.'
    if check == 'account' and not valid_account(value):
        return 'Zkontrolujte číslo účtu nebo IBAN.'
    if check.startswith('zip:'):
        country = answers.get(check[4:] + '_country', '')
        pattern = r'\d{3} ?\d{2}' if czech(country) or not country else r'[A-Za-z0-9 -]{2,12}'
        if not re.fullmatch(pattern, value):
            return 'Zkontrolujte PSČ.'
    return None


def activity(answers, fields=FIELDS):
    """Transitive branch state: a field is active only if its controlling fields are."""
    by_key = {x['key']: x for x in fields}
    memo = {}

    def is_active(key, trail=()):
        if key in memo:
            return memo[key]
        spec = by_key.get(key)
        if spec is None or key in trail:
            return False
        result = all(is_active(ref, trail + (key,)) and answers.get(ref) in values
                     for ref, values in (spec.get('when') or {}).items())
        memo[key] = result
        return result
    return {k: is_active(k) for k in by_key}


def item_activity(spec, row):
    return {x['key']: all(row.get(r) in v for r, v in (x.get('when') or {}).items()) for x in spec['items']}


def clean_item(spec, raw, complete, label, errors, key):
    allowed = {x['key'] for x in spec['items']}
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise ValueError('Položka seznamu obsahuje nepovolená pole.')
    row = {}
    for sub in spec['items']:
        value = raw.get(sub['key'], [] if sub['type'] == 'months' else '')
        if sub['type'] == 'months':
            if (not isinstance(value, list) or len(value) > 12 or len(set(value)) != len(value)
                    or any(not isinstance(m, int) or isinstance(m, bool) or not 1 <= m <= 12 for m in value)):
                errors[key] = 'Měsíce musí být jedinečné hodnoty 1 až 12.'
                value = []
            row[sub['key']] = sorted(value)
            continue
        if not isinstance(value, str) or len(value) > TEXT_LIMIT:
            raise ValueError('Položka seznamu má neplatný formát.')
        row[sub['key']] = value.strip()
    act = item_activity(spec, row)
    for sub in spec['items']:
        value = row[sub['key']]
        if sub['type'] == 'months' or not act[sub['key']]:
            continue
        if value:
            problem = check_value(sub, value, row)
            if problem:
                errors[key] = f'{label}: {sub["label"].lower()} — {problem}'
        elif complete and sub['required']:
            errors[key] = f'Doplňte u položky „{label}“: {sub["label"].lower()}.'
    if complete and key == 'children' and row.get('order') in ['1', '2', '3'] and not row.get('months'):
        errors[key] = f'{label}: vyberte měsíce zamýšleného uplatnění.'
    return row


def normalize(answers, complete=False):
    if not isinstance(answers, dict) or set(answers) - (set(BY_KEY) | {'_review'}):
        raise ValueError('Dotazník obsahuje nepovolená pole.')
    review = answers.get('_review', [])
    if not isinstance(review, list) or any(k not in BY_KEY for k in review) or len(review) > len(BY_KEY):
        raise ValueError('Označení k upřesnění je neplatné.')
    review = sorted(set(review))
    out, errors = {}, {}
    # Normalize strings first so branch activity is computed from clean values.
    for spec in FIELDS:
        key = spec['key']
        if spec['type'] == 'list':
            continue
        value = answers.get(key, '')
        if not isinstance(value, str) or len(value) > (AREA_LIMIT if spec['type'] == 'textarea' else TEXT_LIMIT):
            errors[key] = 'Zadejte text v povolené délce.'
            value = ''
        if key in answers or value:
            out[key] = value.strip()
    act = activity(out)
    for spec in FIELDS:
        key = spec['key']
        if spec['type'] == 'list':
            raw = answers.get(key, [])
            if not isinstance(raw, list) or len(raw) > MAX_LIST:
                raise ValueError('Zkontrolujte seznam položek.')
            if key in answers or raw:
                rows = []
                for i, item in enumerate(raw):
                    rows.append(clean_item(spec, item, complete and act[key], f'{spec["label"]} {i + 1}',
                                           errors if act[key] else {}, key))
                out[key] = rows
            if complete and act[key] and spec.get('min_items') and len(out.get(key, [])) < spec['min_items'] \
                    and key not in review:
                errors[key] = f'Přidejte alespoň jednu položku: {spec["label"].lower()}, nebo ji označte k upřesnění.'
            continue
        value = out.get(key, '')
        if not act[key]:
            continue  # hidden answers are retained, not validated as part of this branch
        if value and key not in errors:
            problem = check_value(spec, value, out)
            if problem:
                errors[key] = problem
        if complete and spec['required'] and not value and key not in review:
            errors[key] = 'Doplňte údaj, nebo ho označte „Potřebuji upřesnit“.'
    if review:
        out['_review'] = review
    if errors:
        raise AnswerError(errors)
    return out


def effective(answers):
    """Only answers from currently active branches become part of a submission."""
    act = activity(answers)
    result = {k: v for k, v in answers.items() if k in BY_KEY and act[k]}
    review = [k for k in answers.get('_review', []) if act.get(k)]
    if review:
        result['_review'] = review
    return result


def hidden(answers):
    act = activity(answers)
    return [BY_KEY[k]['label'] for k, v in answers.items() if k in BY_KEY and not act[k] and v not in ('', [], None)]


def dropped_hidden(previous, new):
    """Hidden non-empty answers that a save would delete; needs explicit confirmation."""
    act = activity(previous)
    return [BY_KEY[k]['label'] for k, v in previous.items()
            if k in BY_KEY and not act[k] and v not in ('', [], None) and new.get(k) in (None, '', [])]


def option_label(spec, value):
    for key, label in spec.get('options') or []:
        if key == value:
            return label
    return value


def expiry_issue(label, value):
    try:
        until = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if until < date.today():
        return f'{label}: platnost skončila {until.strftime("%d. %m. %Y")} — ověřit oprávnění.'
    if until <= date.today() + timedelta(days=60):
        return f'{label}: platnost končí {until.strftime("%d. %m. %Y")} — připravit prodloužení.'
    return None


def review_issues(answers):
    act = activity(answers)
    issues = []
    for spec in FIELDS:
        key = spec['key']
        if not act[key]:
            continue
        if answers.get(key) == 'review':
            issues.append(f'K upřesnění: {spec["label"]}')
        if spec['type'] == 'list':
            for i, row in enumerate(answers.get(key) or []):
                for sub in spec['items']:
                    if row.get(sub['key']) == 'review':
                        issues.append(f'K upřesnění: {spec["label"]} {i + 1} — {sub["label"]}')
    for key in answers.get('_review', []):
        if act.get(key):
            issues.append(f'Označeno k upřesnění: {BY_KEY[key]["label"]}')
    a = lambda k: answers.get(k) if act.get(k) else None  # noqa: E731
    if a('declaration') == 'yes' and a('declaration_elsewhere_status') == 'signed_elsewhere':
        issues.append('Souběh Prohlášení poplatníka — v jednom měsíci jen u jednoho plátce; ověřit období.')
    if a('tax_residency') == 'other':
        issues.append('Daňový nerezident — individuální kontrola účetní.')
    if a('children_claim') == 'yes':
        issues.append('Děti — ověřit nároky, období, pořadí a podklady druhého poplatníka.')
    if a('other_employment') == 'yes':
        issues.append('Souběh zaměstnání — ověřit účast na pojištění a Prohlášení.')
    if a('pension_status') not in (None, '', 'none', 'review'):
        issues.append('Důchod — doložit rozhodnutí; dopad na pojistné a slevy posoudí účetní.')
    if a('enforcement') == 'yes' or a('insolvency') == 'yes':
        issues.append('Srážky ze mzdy — doložit rozhodnutí; pořadí a výpočet určí mzdová účetní.')
    if a('account_holder') == 'other':
        issues.append('Výplata na účet jiné osoby — vyžaduje písemnou žádost zaměstnance.')
    if a('payment_method') == 'cash':
        issues.append('Výplata v hotovosti — potvrdit dohodu s HR.')
    if a('state_insured') == 'yes':
        issues.append('Státní pojištěnec — doložit kategorii.')
    if a('foreign_social_security') == 'yes':
        issues.append('Pojištění v jiném státě — doložit formulář A1.')
    for key in ['id_doc_valid_to', 'residence_valid_to', 'work_permit_valid_to']:
        problem = act.get(key) and expiry_issue(BY_KEY[key]['label'], answers.get(key))
        if problem:
            issues.append(problem)
    return issues


BASE_REQUIREMENTS = [
    ('contract', 'Pracovní smlouva nebo dohoda a dodatky', 'hr'),
    ('payroll_docs', 'Další podklady vyžádané mzdovou účetní', 'payroll'),
    ('medical', 'Pracovnělékařská prohlídka podle kategorie práce', 'hr'),
    ('safety', 'Školení BOZP a PO podle pracoviště', 'safety'),
    ('equipment', 'Předání vybavení a odpovědnosti', 'manager'),
    ('qualification', 'Kvalifikace a platnosti pro pozici', 'hr'),
]

CONDITIONAL_REQUIREMENTS = [
    ('declaration', 'Podepsané Prohlášení poplatníka (podpis zvlášť)', 'payroll', lambda a: a('declaration') == 'yes'),
    ('children_docs', 'Doklady k dětem (např. potvrzení o studiu, ZTP/P)', 'payroll', lambda a: a('children_claim') == 'yes'),
    ('second_taxpayer', 'Potvrzení zaměstnavatele druhého poplatníka', 'payroll',
     lambda a: a('second_taxpayer') in ('claims', 'not_claims')),
    ('foreign_permit', 'Doklad o pobytu a oprávnění k práci, informace úřadu práce', 'hr',
     lambda a: a('citizenship_group') in ('eu', 'third', 'review')),
    ('a1', 'Formulář A1 (pojištění v jiném státě)', 'payroll', lambda a: a('foreign_social_security') == 'yes'),
    ('pension', 'Rozhodnutí o důchodu', 'payroll', lambda a: a('pension_status') not in (None, '', 'none')),
    ('deductions', 'Rozhodnutí o srážkách ze mzdy / insolvenci', 'payroll',
     lambda a: a('enforcement') == 'yes' or a('insolvency') == 'yes'),
    ('account_other', 'Žádost o výplatu na účet jiné osoby', 'payroll', lambda a: a('account_holder') == 'other'),
    ('state_insured', 'Doklad kategorie státního pojištěnce', 'payroll', lambda a: a('state_insured') == 'yes'),
]


def suggested_requirements(answers):
    act = activity(answers)
    a = lambda k: answers.get(k) if act.get(k) else None  # noqa: E731
    return [(rid, label, owner) for rid, label, owner, applies in CONDITIONAL_REQUIREMENTS if applies(a)]
