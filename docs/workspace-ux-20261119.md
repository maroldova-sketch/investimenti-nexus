# NEXUS: společné ovládání a Microsoft 365

## Rozsah změny

Tato varianta změny navazuje přímo na provozní větev `blok-nexus-hr-20261117`, revizi `c19a5fa53fc947d743195e10f92eebf741aa91f6`. Nemění databázi, obchodní záznamy, autentizaci, role ani formulářové kontrakty. Novější fleet pilot z PR17 není součástí této varianty: neobsahuje jeho příkazy, migrace, přepínače ani změny autentizace. Kompatibilita s novější fleet větví je připravena samostatně v PR18.

Společná šablona `frontend/templates/layouts/base.html` sjednocuje 41 existujících stránek: přehled, lidi, pracovní vztahy, docházku, absence, požadavky, schvalování, vozidla, řidiče, jízdy, PHM, AXIGON, importy a Microsoft 365. Spolu s novou chybovou stránkou Microsoft 365 ji používá 42 šablon. Katalog navigace v `layouts/workspace.html` má sedm oblastí s odlišným barevným akcentem. Každá agenda dostává krátký další krok a rozbalitelný postup. Aktivní položka se vybírá podle nejdelšího odpovídajícího URL, takže například srážky mají vlastní kontext i pod obecným vozovým parkem.

Menu má vyhledání bez diakritiky, klávesovou zkratku Ctrl/⌘ K, samostatně ovládané mobilní zobrazení a odkaz pro přeskočení na obsah. Filtr menu nemění formuláře ani jejich hodnoty. Po vymazání hledání vrátí předchozí rozbalení oblastí. Tlačítko „Jak na to“ otevře postup příslušné stránky.

Do nové navigace se nezařazují neimplementované `/dashboard`, `/entities`, `/bank`, `/sync` a `/audit`. Jejich route ani obchodní data se nemažou. Obecný přehled vede na existující `/atlas`. FORTIS zůstává původním odkazem označeným jako dostupný v místní síti; odkaz nepotvrzuje synchronizaci nebo funkčnost připojení. Veřejné API FORTIS se nevydává za webové uživatelské rozhraní.

Samostatný HR průvodce dostává odpovídající fialový akcent, čitelnější drobné texty a český popisek pro návrat. Formulář, validátory, revize, soubory a oddělený vstup pro zaměstnance zůstávají beze změny.

## Opravené funkční chyby

Konkrétní routy `/fleet/trips` a `/fleet/phm` se registrují před `/fleet/{vehicle_id}`. Dříve je obecný detail vozidla zachytil jako ID `trips` a `phm`. Obdobně `/m365/mail/search` a `/m365/mail/compose` nyní předcházejí `/m365/mail/{message_id}`.

Čtení Outlooku, kalendáře, kontaktů a OneDrive rozlišuje chybějící přístup, chybějící záznam, omezení počtu požadavků, nedostupnou síť a poruchu poskytovatele. Návodná chybová stránka nepředstírá úspěšně načtený prázdný seznam. Nevypisuje surové výjimky, tokeny ani chybové tělo Microsoftu. Respektuje `Retry-After`; nic samo neopakuje. Zápis a odesílání pošty se nemění.

## Ověření

```text
python -m unittest discover -s tests -p test_workspace_shell.py -v
node --check frontend/static/js/workspace.js
git diff --check
```

12 testů ověřuje kompilaci všech šablon, správné aktivní oblasti a jedinečné menu, všechny navigační cíle proti registrovanému FastAPI routeru, čtyři opravené kolize rout, skutečné GET zpracování hledání a psaní pošty, chybové stavy Microsoftu, nezobrazení soukromé diagnostiky a dodržení čekání poskytovatele. Microsoft a uživatel jsou v těchto testech izolované náhrady; žádná zpráva se neodesílá a produkční databáze se nepoužívá.

Testy neprokazují produkční nasazení, aktuální platnost Microsoft 365 přihlášení ani přenos dat mezi NEXUS a FORTIS. Při publikaci je třeba znovu porovnat head provozní větve a zachovat případné další změny. FORTIS frontend nebyl měněn: v dostupném GitHub stromu nebyl doložen jeho kanonický zdrojový kód.
