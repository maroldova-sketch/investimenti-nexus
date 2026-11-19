# NEXUS: společné ovládání a Microsoft 365

## Rozsah změny

Změna navazuje na aktuální fleet větev `feat/fleet-elias-p0-20261118`, revizi `30849637c610b1bd14d9a40a3f68d132f66dce8a` (PR17), která zahrnuje HR revizi `c19a5fa53fc947d743195e10f92eebf741aa91f6` (PR15). Nemění databázi, obchodní záznamy, autentizaci, role ani formulářové kontrakty. Zachovává pilotní bránu vozového parku, auditované příkazy, kontrolu oprávnění a vypnuté HTTP importní spouštěče z PR17.

Společnou šablonu `frontend/templates/layouts/base.html` používá 43 stránek včetně nové chybové stránky Microsoft 365: přehled, lidi, pracovní vztahy, docházku, absence, požadavky, schvalování, vozidla, řidiče, jízdy, PHM, AXIGON, importy a Microsoft 365. Katalog navigace v `layouts/workspace.html` má sedm oblastí s odlišným barevným akcentem. Každá agenda dostává krátký další krok a rozbalitelný postup. Aktivní položka se vybírá podle nejdelšího odpovídajícího URL, takže například srážky mají vlastní kontext i pod obecným vozovým parkem. Kilometry a závady mají vlastní návod a odkaz se objeví jen při zapnutém existujícím fleet pilotu.

Menu má vyhledání bez diakritiky, klávesovou zkratku Ctrl/⌘ K, samostatně ovládané mobilní zobrazení a odkaz pro přeskočení na obsah. Filtr menu nemění formuláře ani jejich hodnoty. Po vymazání hledání vrátí předchozí rozbalení oblastí. Tlačítko „Jak na to“ otevře postup příslušné stránky.

Do nové navigace se nezařazují neimplementované `/dashboard`, `/entities`, `/bank`, `/sync` a `/audit`. Jejich route ani obchodní data se nemažou. Obecný přehled vede na existující `/atlas`. FORTIS zůstává původním odkazem označeným jako dostupný v místní síti; odkaz nepotvrzuje synchronizaci nebo funkčnost připojení. Veřejné API FORTIS se nevydává za webové uživatelské rozhraní.

Samostatný HR průvodce dostává odpovídající fialový akcent, čitelnější drobné texty a český popisek pro návrat. Formulář, validátory, revize, soubory a oddělený vstup pro zaměstnance zůstávají beze změny.

## Opravené funkční chyby

Podklad z PR17 již registruje konkrétní routy `/fleet/trips` a `/fleet/phm` před `/fleet/{vehicle_id}` a tato oprava zůstává zachovaná včetně závislostí pro oprávnění. Změna opravuje obdobnou kolizi: `/m365/mail/search` a `/m365/mail/compose` nyní předcházejí `/m365/mail/{message_id}`.

Čtení Outlooku, kalendáře, kontaktů a OneDrive rozlišuje chybějící přístup, chybějící záznam, omezení počtu požadavků, nedostupnou síť a poruchu poskytovatele. Návodná chybová stránka nepředstírá úspěšně načtený prázdný seznam. Nevypisuje surové výjimky, tokeny ani chybové tělo Microsoftu. Respektuje `Retry-After`; nic samo neopakuje. Zápis a odesílání pošty se nemění.

## Ověření

```text
python -m unittest discover -s tests -p test_workspace_shell.py -v
python -m unittest discover -s tests -p test_fleet_bootstrap.py -v
node --check frontend/static/js/workspace.js
git diff --check
```

13 testů ověřuje kompilaci všech šablon, správné aktivní oblasti a jedinečné menu, navigační cíle proti registrovanému FastAPI routeru, nezobrazení vypnutých modulů HR a fleet pilotu, čtyři kolize rout, skutečné GET zpracování hledání a psaní pošty, chybové stavy Microsoftu, nezobrazení soukromé diagnostiky a dodržení čekání poskytovatele. Microsoft a uživatel jsou v těchto testech izolované náhrady; žádná zpráva se neodesílá a produkční databáze se nepoužívá. Další čtyři existující fleet bootstrap testy kontrolují nečinné importní spouštěče, uzavření pilotu bez schématu a bezpečné chování jeho instalátoru na dočasné databázi.

Testy neprokazují produkční nasazení, aktuální platnost Microsoft 365 přihlášení ani přenos dat mezi NEXUS a FORTIS. Při publikaci je třeba znovu porovnat head cílové větve a zachovat případné další změny. FORTIS frontend nebyl měněn: v dostupném GitHub stromu nebyl doložen jeho kanonický zdrojový kód.
