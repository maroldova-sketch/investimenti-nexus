"""
Seed Czech name day calendar + generate PersonCalendarEvents from person DB.
Covers all 366 days, source: official Czech name day calendar.
"""
import unicodedata
from backend.core.models.base import SessionLocal
from backend.core.models.kernel import Person
from .calendar_models import CzechNameDay, PersonCalendarEvent

# Official Czech name day calendar — (month, day): [names]
CZECH_NAMEDAYS = {
    (1,1):['Nový rok','Nový rok'],(1,2):['Karina'],(1,3):['Radmila'],(1,4):['Diana'],(1,5):['Dalimil'],
    (1,6):['Tři králové','Kašpar','Melichar','Baltazar'],(1,7):['Vilma'],(1,8):['Čestmír'],(1,9):['Vladan'],
    (1,10):['Břetislav'],(1,11):['Bohdana'],(1,12):['Pravoslav'],(1,13):['Edita'],(1,14):['Radovan'],
    (1,15):['Alice'],(1,16):['Ctirad'],(1,17):['Drahoslav'],(1,18):['Vladislav'],(1,19):['Doubravka'],
    (1,20):['Ilona'],(1,21):['Běla'],(1,22):['Slavomír'],(1,23):['Zdeněk'],(1,24):['Milena'],
    (1,25):['Miloš'],(1,26):['Zora'],(1,27):['Ingrid'],(1,28):['Otýlie'],(1,29):['Zdislava'],
    (1,30):['Robin','Roberta'],(1,31):['Marika'],
    (2,1):['Hynek'],(2,2):['Nela'],(2,3):['Blažej'],(2,4):['Jarmila'],(2,5):['Dobromila'],
    (2,6):['Vanda'],(2,7):['Veronika'],(2,8):['Milada'],(2,9):['Apolena'],(2,10):['Mojmír'],
    (2,11):['Božena'],(2,12):['Slavěna'],(2,13):['Věnceslava'],(2,14):['Valentýn','Valentýna'],
    (2,15):['Jiřina'],(2,16):['Ljuba'],(2,17):['Miloslava'],(2,18):['Gizela'],(2,19):['Patrik','Vlastimil'],
    (2,20):['Oldřich'],(2,21):['Lenka'],(2,22):['Isabela'],(2,23):['Svatopluk'],(2,24):['Matěj'],
    (2,25):['Liliana'],(2,26):['Dorota'],(2,27):['Alexandr'],(2,28):['Lumír'],(2,29):['Horymír'],
    (3,1):['Bedřich'],(3,2):['Anežka'],(3,3):['Kamil'],(3,4):['Stela'],(3,5):['Kazimír'],
    (3,6):['Miroslav'],(3,7):['Tomáš'],(3,8):['Gabriela'],(3,9):['Františka'],(3,10):['Viktorie'],
    (3,11):['Anděla'],(3,12):['Řehoř'],(3,13):['Růžena'],(3,14):['Matylda'],(3,15):['Oldřiška'],
    (3,16):['Hynek'],(3,17):['Vlastimil'],(3,18):['Eduard'],(3,19):['Josef'],(3,20):['Světlana'],
    (3,21):['Radek'],(3,22):['Leona'],(3,23):['Ivona'],(3,24):['Gabriel'],(3,25):['Marián','Marian'],
    (3,26):['Emanuel'],(3,27):['Dita'],(3,28):['Soňa'],(3,29):['Taťána'],(3,30):['Arnošt'],(3,31):['Kvido'],
    (4,1):['Hugo'],(4,2):['Erika'],(4,3):['Richard'],(4,4):['Ivana'],(4,5):['Miroslava'],
    (4,6):['Vendula'],(4,7):['Heřman'],(4,8):['Ema'],(4,9):['Dušan'],(4,10):['Darja'],
    (4,11):['Izabela'],(4,12):['Julius'],(4,13):['Aleš'],(4,14):['Vincenc'],(4,15):['Anastázie'],
    (4,16):['Irena'],(4,17):['Rudolf'],(4,18):['Valerie'],(4,19):['Rostislav'],(4,20):['Marcela'],
    (4,21):['Alexandra'],(4,22):['Evžénie'],(4,23):['Vojtěch'],(4,24):['Jiří'],(4,25):['Marek'],
    (4,26):['Oto'],(4,27):['Jaroslav'],(4,28):['Vlastislav'],(4,29):['Robert'],(4,30):['Blahoslav'],
    (5,1):['Svátek práce'],(5,2):['Zikmund'],(5,3):['Alexej'],(5,4):['Květoslav'],(5,5):['Klaudie'],
    (5,6):['Radoslav'],(5,7):['Stanislav'],(5,8):['Den vítězství'],(5,9):['Ctibor'],(5,10):['Blažena'],
    (5,11):['Svatava'],(5,12):['Pankrác'],(5,13):['Servác'],(5,14):['Bonifác'],(5,15):['Žofie','Žofia'],
    (5,16):['Přemysl'],(5,17):['Aneta'],(5,18):['Nataša'],(5,19):['Ivo'],(5,20):['Zbyšek'],
    (5,21):['Monika'],(5,22):['Emil'],(5,23):['Vladimír'],(5,24):['Jana'],(5,25):['Viola'],
    (5,26):['Filip'],(5,27):['Valdemar'],(5,28):['Vilém'],(5,29):['Maxmilián'],(5,30):['Ferdinand'],
    (5,31):['Petronela'],
    (6,1):['Laura'],(6,2):['Jarmil'],(6,3):['Tamara'],(6,4):['Dalibor'],(6,5):['Dobroslav'],
    (6,6):['Norbert'],(6,7):['Iveta'],(6,8):['Medard'],(6,9):['Stanislava'],(6,10):['Gita'],
    (6,11):['Bruno'],(6,12):['Antonie'],(6,13):['Antonín'],(6,14):['Roland'],(6,15):['Vít'],
    (6,16):['Zbyněk'],(6,17):['Adolf'],(6,18):['Milan'],(6,19):['Leoš'],(6,20):['Dagmar'],
    (6,21):['Alois'],(6,22):['Pavla'],(6,23):['Zdeňka'],(6,24):['Jan'],(6,25):['Ivan'],
    (6,26):['Adriana'],(6,27):['Ladislav'],(6,28):['Lubomír'],(6,29):['Petr','Pavel'],(6,30):['Šárka'],
    (7,1):['Jaroslava'],(7,2):['Patricie'],(7,3):['Radomír'],(7,4):['Prokop'],(7,5):['Cyril','Metoděj'],
    (7,6):['Jan Hus'],(7,7):['Bohuslava'],(7,8):['Nelly'],(7,9):['Drahomíra'],(7,10):['Libuše','Amálie'],
    (7,11):['Olga'],(7,12):['Bořek'],(7,13):['Markéta'],(7,14):['Karolína'],(7,15):['Jindřich'],
    (7,16):['Luboš'],(7,17):['Martina','Luboš'],(7,18):['Drahota'],(7,19):['Čeněk'],(7,20):['Ilja'],
    (7,21):['Vítězslav'],(7,22):['Magdaléna'],(7,23):['Libor'],(7,24):['Kristýna'],(7,25):['Jakub'],
    (7,26):['Anna'],(7,27):['Věroslav'],(7,28):['Viktor'],(7,29):['Marta'],(7,30):['Bořivoj'],
    (7,31):['Ignác'],
    (8,1):['Oskar'],(8,2):['Gustav'],(8,3):['Miluše'],(8,4):['Dominik'],(8,5):['Kristián'],
    (8,6):['Oldřich'],(8,7):['Lada'],(8,8):['Soběslav'],(8,9):['Roman'],(8,10):['Vavřinec','Vavřin'],
    (8,11):['Zuzana','Suzana'],(8,12):['Klára'],(8,13):['Alžběta'],(8,14):['Arnošt'],(8,15):['Hana'],
    (8,16):['Jáchym'],(8,17):['Petra'],(8,18):['Helena','Heleňa'],(8,19):['Ludvík'],(8,20):['Bernard'],
    (8,21):['Johana'],(8,22):['Bohuslav'],(8,23):['Sandra'],(8,24):['Bartoloměj'],(8,25):['Radim'],
    (8,26):['Luděk'],(8,27):['Otakar'],(8,28):['Augustýn'],(8,29):['Evelína'],(8,30):['Vladěna'],
    (8,31):['Pavlína'],
    (9,1):['Linda'],(9,2):['Adéla'],(9,3):['Bronislav'],(9,4):['Jindřiška'],(9,5):['Boris'],
    (9,6):['Boleslav'],(9,7):['Regína'],(9,8):['Mariana'],(9,9):['Daniela'],(9,10):['Irma'],
    (9,11):['Denisa'],(9,12):['Marie'],(9,13):['Lubor'],(9,14):['Radka'],(9,15):['Jolana'],
    (9,16):['Ludmila'],(9,17):['Naděžda'],(9,18):['Kryštof'],(9,19):['Zita'],(9,20):['Oleg'],
    (9,21):['Matouš'],(9,22):['Darina'],(9,23):['Bořivoj'],(9,24):['Jaromír'],(9,25):['Zlata'],
    (9,26):['Andrea'],(9,27):['Jonáš'],(9,28):['Václav'],(9,29):['Michal'],(9,30):['Jeroným'],
    (10,1):['Igor'],(10,2):['Olívie','Oliva'],(10,3):['Bohumil'],(10,4):['František'],(10,5):['Eliška'],
    (10,6):['Hanuš'],(10,7):['Justýna'],(10,8):['Věra'],(10,9):['Štefan','Štefan'],(10,10):['Marina'],
    (10,11):['Andrej'],(10,12):['Marcel'],(10,13):['Renáta'],(10,14):['Agáta'],(10,15):['Tereza'],
    (10,16):['Havel'],(10,17):['Hedvika'],(10,18):['Lukáš'],(10,19):['Michaela'],(10,20):['Vendelín'],
    (10,21):['Brigita'],(10,22):['Sabina'],(10,23):['Teodor'],(10,24):['Nina'],(10,25):['Beáta'],
    (10,26):['Erik'],(10,27):['Šarlota'],(10,28):['Den vzniku ČSR','Zánik Československa'],(10,29):['Silvie'],
    (10,30):['Tadeáš'],(10,31):['Štěpánka'],
    (11,1):['Felix'],(11,2):['Dušičky'],(11,3):['Hubert'],(11,4):['Karel'],(11,5):['Miriam'],
    (11,6):['Liběna'],(11,7):['Saskie'],(11,8):['Bohumír'],(11,9):['Bohdan'],(11,10):['Evžen'],
    (11,11):['Martin'],(11,12):['Benedikt'],(11,13):['Tibor'],(11,14):['Sáva'],(11,15):['Leopold'],
    (11,16):['Otmar'],(11,17):['Mahulena'],(11,18):['Romana'],(11,19):['Alžběta'],(11,20):['Nikola'],
    (11,21):['Albert'],(11,22):['Cecílie'],(11,23):['Klement'],(11,24):['Jana'],(11,25):['Kateřina'],
    (11,26):['Artur'],(11,27):['Xenie'],(11,28):['René'],(11,29):['Zina'],(11,30):['Ondřej'],
    (12,1):['Iva'],(12,2):['Blanka'],(12,3):['Svatoslav'],(12,4):['Barbora'],(12,5):['Jitka'],
    (12,6):['Mikuláš'],(12,7):['Ambrož'],(12,8):['Květoslava'],(12,9):['Vratislav'],(12,10):['Julie'],
    (12,11):['Dana'],(12,12):['Simona'],(12,13):['Lucie'],(12,14):['Lýdie'],(12,15):['Radana'],
    (12,16):['Albína'],(12,17):['Daniel'],(12,18):['Miloslav'],(12,19):['Ester'],(12,20):['Dagmar'],
    (12,21):['Natálie'],(12,22):['Šimon'],(12,23):['Vlasta'],(12,24):['Adam','Eva'],(12,25):['Boží hod'],
    (12,26):['Štěpán'],(12,27):['Žaneta'],(12,28):['Bohumila'],(12,29):['Judita'],(12,30):['David'],
    (12,31):['Silvester'],
}

def normalize_name(name):
    """Remove diacritics, lowercase for matching."""
    nfkd = unicodedata.normalize('NFKD', name.lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def seed_namedays(db):
    if db.query(CzechNameDay).count() > 0:
        print("Name days already seeded.")
        return
    entries = []
    for (month, day), names in CZECH_NAMEDAYS.items():
        for name in names:
            entries.append(CzechNameDay(
                day=day, month=month,
                name=name,
                name_normalized=normalize_name(name),
            ))
    db.bulk_save_objects(entries)
    db.commit()
    print(f"Seeded {len(entries)} Czech name day entries.")


def seed_person_events(db):
    """Generate PersonCalendarEvents from existing Person records."""
    from datetime import date
    people = db.query(Person).filter(Person.is_active == True).all()
    created = 0

    for p in people:
        # Skip if already has events
        existing = db.query(PersonCalendarEvent).filter(
            PersonCalendarEvent.person_id == p.id
        ).count()
        if existing: continue

        # Birthday
        if p.birth_date:
            try:
                bd = p.birth_date if hasattr(p.birth_date, 'month') else date.fromisoformat(str(p.birth_date)[:10])
                db.add(PersonCalendarEvent(
                    person_id=p.id,
                    event_type="birthday",
                    day=bd.day, month=bd.month, year=bd.year,
                    label=f"Narozeniny — {p.full_name}",
                    notify_days_before=7,
                ))
                created += 1
            except: pass

        # Work anniversary
        if p.hire_date:
            try:
                hd = p.hire_date if hasattr(p.hire_date, 'month') else date.fromisoformat(str(p.hire_date)[:10])
                db.add(PersonCalendarEvent(
                    person_id=p.id,
                    event_type="work_anniversary",
                    day=hd.day, month=hd.month, year=hd.year,
                    label=f"Výročí nástupu — {p.full_name}",
                    notify_days_before=7,
                ))
                created += 1
            except: pass

        # Name day — match first name against Czech calendar
        if p.first_name:
            fn_norm = normalize_name(p.first_name.strip())
            match = db.query(CzechNameDay).filter(
                CzechNameDay.name_normalized == fn_norm
            ).first()
            if match:
                db.add(PersonCalendarEvent(
                    person_id=p.id,
                    event_type="nameday",
                    day=match.day, month=match.month, year=None,
                    label=f"Jmeniny — {p.full_name}",
                    notify_days_before=3,
                ))
                created += 1

    db.commit()
    print(f"PersonCalendarEvents created: {created}")


if __name__ == "__main__":
    from backend.core.models.base import SessionLocal, Base, engine
    from backend.modules.people.calendar_models import PersonCalendarEvent, HoldingCalendarEvent, CzechNameDay
    Base.metadata.create_all(engine)
    db = SessionLocal()
    seed_namedays(db)
    seed_person_events(db)
    db.close()
