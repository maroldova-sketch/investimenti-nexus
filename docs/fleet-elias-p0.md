# Vozový park: provoz přes Eliase – P0, 18. 11. 2026

Implementace navazuje na existující NEXUS a jeho kanonickou databázi. Nevytváří další samostatnou aplikaci ani databázi. Tato změna sama nezajišťuje veřejný ingress nebo napojení živého Eliase. Nasazení a skutečný online průchod zůstávají samostatným ověřitelným krokem.

## Funkční rozsah

- `/fleet/operations`: vyhledání auta, karta, historie, odečet kilometrů a závada; mobilní rozhraní pro správce.
- `/api/fleet/elias/*`: stejný autorizovaný zápis pro Eliase; existující přihlášení NEXUS, platný holdingový owner/admin/fleet_manager. Žádný nový sdílený servisní účet.
- Odečet/závada, audit a potvrzení příkazu v jedné transakci. Revize vozidla brání přepsání souběžné změny; unikátní klíč řeší opakované doručení.
- Potvrzení uživateli až po zpětném GET ověření obsahu. Timeout: opakovat přesně původní požadavek se stejným klíčem, časem i revizí.
- Nejasná PHM zůstávají viditelná k ověření. Denní předání se společným datem není automaticky přiřazeno. Měsíční souhrn potřebuje jedno nesporné svěření přes celý měsíc. Součty vozidel a osob používají stejná schválená data a Decimal.
- Původní anonymní HTTP importy jsou vypnuté (410), i bez aktivace pilotu. Import musí proběhnout kontrolovaně lokálně po záloze.

## Zapnutí v existujícím prostředí

1. Ověřit kanonickou DB a připravit ověřenou zálohu včetně SQLite WAL, pokud je aktivní. Discovery identifikovalo `~/Projects/nexus/nexus.db`; cestu musí ověřit nasazující proces, nikoli odvodit z cwd.
2. Nad oddělenou kopií DB nejdříve provést dry run a test:
   ```sh
   .venv/bin/python scripts/install_fleet_command_schema.py --database-url sqlite:////ABSOLUTNI/CESTA/nexus.db
   ```
   Teprve s existující zálohou stejný příkaz s `--apply`. Přidává pouze tabulku `fleet_command`; nemění vozidla, PHM ani historii. Start aplikace tabulky nevytváří.
3. Nastavit `DATABASE_URL` na kanonickou absolutní cestu, zachovat existující silný `SECRET_KEY` (výchozí vývojový klíč je odmítnut), `NEXUS_FLEET_ELIAS_ENABLED=1` a `NEXUS_RELEASE_SHA` na skutečný nasazený commit. Nezapínat na náhodné prázdné DB. `release` v API je konfigurační údaj, ne nezávislý důkaz běžícího kódu.
4. Použít jeden existující pracovní vstup a routy NEXUS pro `/fleet`, `/api/fleet`, `/static` a stávající přihlášení. Nevystavovat celý backend přes veřejný HR ingress. Před vystavením zkontrolovat i ostatní dostupné routy aplikace; tento patch není audit celého ERP.
5. Ověřit nejprve nepřihlášený a nepovolený přístup, potom skutečný zápis + readback pod oprávněným správcem. Syntetická testovací data patří do oddělené DB, ne do produkční flotily.
6. Vrácení: vypnout feature flag a vrátit aplikaci dle provozního postupu. Aditivní tabulku ani již zapsané záznamy nemažte. Vypnutí pilotu vrací staré řízení přístupu, proto nesmí ponechat nový online ingress bez ochrany.

Pilot záměrně povoluje na starších fleet/AXIGON/import obrazovkách jen čtení a vyžaduje stejný holdingový mandát. Nepodporované zápisy vrací 409. To dočasně omezuje i staré formuláře; plné opravy a firemně omezené role vyžadují další implementaci. Rozhraní nesmí být vydáváno za hotový zaměstnanecký portál.

## Kontrakt Eliase

1. Použít přihlášenou identitu oprávněného správce v NEXUS. GET `/api/fleet/elias/meta` vrací CSRF hodnotu vázanou na aktuální token. Nesdělovat ani nelogovat token/CSRF do konverzace.
2. GET `/api/fleet/elias/vehicles?q=...`; pokud se shoduje více aut, nehádat. GET konkrétního auta vrací `revision`.
3. Z přirozeného zadání připravit skutečný stav tachometru nebo popis závady, datum s časovým posunem a jednoznačné auto. Nezaměňovat ujetou vzdálenost za stav tachometru. API samo volný text neinterpretuje.
4. POST `/api/fleet/elias/commands`, Content-Type application/json a `X-Fleet-CSRF` z meta:
   ```json
   {
     "vehicle_id": "EXISTUJICI-ID-AUTA",
     "expected_revision": "REVIZE-Z-GET",
     "idempotency_key": "55bd4a34-7650-45b0-a6b3-dc1e48f37cd6",
     "kind": "odometer",
     "effective_at": "2026-11-18T08:00:00+01:00",
     "source": "elias",
     "km": 123456
   }
   ```
   Každý nový úmysl potřebuje nový UUID; retry nikoli. Pro závadu použít kind `defect`, pole `description` (1–2000 znaků), vynechat `km`. Odečet je celé číslo 0–9999999. Čas musí obsahovat zónu a nesmí být budoucí. Oprava již existujícího dne je zvláštní workflow, nikoli druhý odečet.
5. GET `/api/fleet/elias/commands/{id}` a ověřit `status=recorded`, ID auta a příkazu. Endpoint porovnává skutečné uložené údaje. Teprve pak „Uloženo“. Poté načíst novou kartu/revizi.
6. Při 409 nezakládat naslepo nový příkaz. Při timeoutu/503 zopakovat původní payload a klíč, následně readback. Při 401/403 obnovit legitimní přihlášení. Finanční operace, objednávky nebo zprávy nejsou součástí tohoto API.

## Přesné hranice

- Živý nástroj Eliase musí být ještě připojen k tomuto kontraktu. Samotné vytvoření endpointů to nedokazuje.
- Příkaz čekající na ověření je v prohlížeči jen v paměti. Stránka varuje před zavřením; po skutečném reloadu se klíč ztratí. Nejistý záznam proto nejprve ověřit v historii. Automatické obnovení rozpracovaných příkazů je další krok.
- PHM přebírá přesnost DB `Numeric(10,2)`; neobnovuje čtyřmístnou přesnost historického XLSX a nededuplikuje měsíční versus denní podklady bez doložené vazby. Nejde o potvrzení fakturace.
- Opravené vyúčtování z 22. 9. 2026 má přednost před starším mappingem. Tento patch je neimportuje a nevytváří trvalé přiřazení řidiče podle historické faktury.
- P1: úplná historie svěření a opravy, měsíční uzávěrka a doklady, STK/pojištění/servis, nákup/prodej/odkup/vrácení leasingu, importy a firemní role. P2: ověřené konektory/telematika/WhatsApp. Identita systému EKO musí být doložena; nevytváří se domnělé napojení.

## Ověření

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_fleet*.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_hr*.py' -v
node --check frontend/static/fleet/operations.js
git diff --check
```

Veškeré automatické testy používají syntetické DB. Produkční migrace, restart, vystavení ingressu ani merge do automaticky nasazované větve nejsou součástí samotné přípravy této změny.
