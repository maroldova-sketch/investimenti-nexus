# D. Nová architektura webu

## D1. Verdikt k jednostránkovému konceptu

Jednostránkový web **neumožňuje organický růst**: 1 URL = 1 title = 1 záměr. Google nemůže zařadit stejnou stránku na „svatba na zámku Louny“ i „letní divadlo“ i „firemní večírek“. Každý produkt potřebuje vlastní URL, title, H1, obsah, schema a konverzi. Homepage zůstane jako rozcestník s brandem.

Ochrana stávající návštěvnosti: web má jen `/` a kotvy; organická návštěvnost je dnes nulová (GSC), takže migrace nic neohrožuje. Kotvy `#zazitky`, `#pribeh`, `#fotografie`, `#kontakt`, `#vstupenky` zachovat na homepage (mohou být v newsletterech/sociálních sítích) a přidat 301: `/#vstupenky` nelze přesměrovat (fragment), proto sekce na homepage ponechat jako zkrácené verze s odkazem na plné stránky.

## D2. Sitemap (fáze 1 = do 60 dnů, fáze 2 = do března 2027, fáze 3 = sezóna)

```
/                               Homepage – rozcestník, program nejbližších akcí, 5 produktů         [F1]
/program                        Kalendář všech akcí (filtr: divadlo, koncerty, gastro, slavnosti)   [F1]
/program/[slug]                 Detail akce (Event schema, vstupenky, interpret, čas, mapa)          [F1]
/divadlo                        Zámecká Resonance – scéna, kapacita, sezóna 2027, předprodej        [F1]
/koncerty                       Hudba na nádvoří a v zahradním sále                                 [F2]
/svatby                         Hub – proč, prostory, kapacity, od-ceny, proces, FAQ, poptávka      [F1]
/svatby/prostory                Nádvoří, arkády, sál, zahrada, apartmá – fotky, kapacity, plány     [F2]
/svatby/cenik-a-podminky        Orientační ceny, co je v ceně, limity 2027                          [F2]
/firemni-akce                   Hub B2B – typy akcí, kapacity, catering, technika, poptávka         [F1]
/pronajem-prostor               Pronájem pro soukromé oslavy, natáčení, galavečery                  [F2]
/prostory/[slug]                Technický list každého prostoru (plocha, kapacita, technika, foto)  [F2]
/gastronomie                    Kuchyně, šéfkuchař, sezónní kalendář chutí, rezervace               [F2]
/slavnosti                      Sezónní a komunitní akce (Halloween, Dušičky, advent, pouť)         [F2]
/historie                       Dějiny zámku, Pachtové, hudební tradice, sochy                      [F1]
/obnova-zamku                   Deník obnovy – timeline, fotoreporty, co se právě děje             [F1]
/obnova-zamku/[slug]            Jednotlivé kapitoly / články                                        [F2]
/navsteva                       Jak se dostat, parkování, otevírací doba, bezbariérovost, pravidla  [F1]
/fotografie                     Galerie (skutečné fotky) + odkaz na „Sdílejte své snímky“           [F1]
/pamet-mista                    Sběr historických fotografií a příběhů (stávající formulář)         [F1]
/kontakt                        Telefon, e-mail, adresa, mapa, IČO, fakturační údaje, tým           [F1]
/novinky                        Newsletter hub + archiv kampaní                                     [F2]
/o-nas                          Kdo za tím stojí, vize Il Senso Vero, tým, partneři                 [F2]
/ochrana-osobnich-udaju         GDPR, cookies (stávající dialog → stránka)                           [F1]
/obchodni-podminky-vstupenky    Podmínky prodeje vstupenek (nutné pro ticketing)                    [F2]
/en, /en/weddings, /en/corporate-events, /en/programme                                              [F3]
```

Hub-and-spoke: každý hub odkazuje na své spokes a zpět; homepage odkazuje na všech 6 hubů (program, divadlo, svatby, firemní akce, gastronomie, historie/obnova); patička na všechny stránky úrovně 1.

## D3. Uživatelské cesty

**Svatba:** Google „svatba na zámku Ústecký kraj“ → `/svatby` (hero fotka nádvoří, 3 argumenty, od-cena) → `/svatby/prostory` (galerie, kapacity) → `/svatby/cenik-a-podminky` → poptávka (4 kroky) → auto-odpověď + telefonát do 24 h → prohlídka (kalendář) → nabídka (PDF z interního systému) → záloha → termín rezervován → e-mail série „před svatbou“ → po svatbě: žádost o recenzi + fotky se souhlasem.

**Divadlo:** Google/Seznam/FB „letní divadlo Louny“ nebo newsletter → `/program` → `/program/[akce]` → „Koupit vstupenky“ (ticketing v iframe/redirect, UTM) → výběr sektoru (hlavní / VIP arkády) → upsell (gastro balíček, parkování, program) → potvrzení → připomínka 48 h → po akci: „Jak se vám líbilo“ + doporučení dalších akcí + sleva na další.

**Firemní event:** LinkedIn/Google „vánoční večírek zámek“ → `/firemni-akce` (reference, kapacity, co zařídíme) → `/prostory/[slug]` (technický list PDF ke stažení za e-mail – volitelně) → nezávazná poptávka (firma, typ, hosté, termín, rozpočet) → obchodní nabídka do 48 h → prohlídka → smlouva.

**Newsletter:** jakákoli stránka → kontextový formulář (zdroj = stránka: svatby/program/gastro/novinky) → double opt-in (Ecomail) → tag zájmu → welcome série 3 e-maily (příběh, co chystáme, první nabídka) → segmentované kampaně.

**Komunitní/historie:** Google „Cítoliby zámek historie“ → `/historie` → `/obnova-zamku` → `/pamet-mista` (sdílení fotek) nebo newsletter „Deník obnovy“.

## D4. Specifikace stránek (účel, cílovka, KW, title, meta, H1, osnova, foto, CTA, odkazy, schema, konverze)

### Homepage `/`
- **Účel/cílovka:** rozcestník; brand; návštěvník, který zná jméno zámku nebo přišel ze sociálních sítí.
- **KW:** zámek Cítoliby (primární), Zámecká Resonance, zámek Louny (sekundární).
- **Title (≤60):** `Zámek Cítoliby – divadlo, svatby a gastronomie u Loun`
- **Description (≤155):** `Barokní zámek u Loun se probouzí. Letní divadlo Zámecká Resonance 2027, svatby, firemní akce a zámecká gastronomie. Program a předprodej vstupenek.`
- **H1:** `Zámek Cítoliby — divadlo, svatby a gastronomie na barokním zámku u Loun`
- **Osnova:** H2 Nejbližší akce (3 karty z /program) · H2 Co u nás zažijete (6 dlaždic → huby) · H2 Sezóna 2027: Zámecká Resonance (předprodej CTA) · H2 Svatby 2027 — zbývá X termínů (lead CTA) · H2 Proč Cítoliby (citát J. Čáky, Il Senso Vero) · H2 Deník obnovy (3 poslední) · H2 Novinky e-mailem.
- **Foto:** skutečný zámek v podvečer (hero), nádvoří, detail erbu, obnova.
- **CTA primární:** „Program a vstupenky“; sekundární: „Poptat svatbu“, „Novinky e-mailem“.
- **Odkazy:** všech 6 hubů, /kontakt, /navsteva.
- **Schema:** Organization, WebSite, Place/TouristAttraction, BreadcrumbList (ne).
- **Konverze:** `cta_click{target}`, `newsletter_signup`.

### `/svatby`
- **Účel/cílovka:** snoubenci 27–38, Praha + severozápadní Čechy; generovat kvalifikované poptávky.
- **KW:** svatba na zámku, svatba na zámku Ústecký kraj, svatební místo poblíž Prahy, svatba Louny.
- **Title:** `Svatba na zámku Cítoliby u Loun | 60 min od Prahy, 5 termínů 2027`
- **Description:** `Prémiová svatba na soukromém barokním zámku 60 minut od Prahy. Nádvoří s arkádami, zahrada, sál, apartmá pro novomanžele a profesionální tým. V roce 2027 jen 5 svateb.`
- **H1:** `Svatba na zámku Cítoliby`
- **Osnova:** H2 Proč se vzít v Cítolibech (3 argumenty + foto) · H2 Prostory a kapacity (nádvoří 200 / sál X / zahrada X – tabulka) · H2 Jak probíhá svatba u nás (časová osa dne) · H2 Co zařídíme (koordinace, catering, ubytování, hudba) · H2 Orientační ceny 2027 (od … Kč, co zahrnuje) · H2 Volné termíny 2027 (kalendář: 5 slotů, obsazené šedě) · H2 Časté otázky (10 Q&A: déšť, kapacita, vlastní catering, noční klid, parkování, ubytování hostů, obřad civilní/církevní, matrika Louny poplatek) · H2 Poptávka (formulář) · H2 Reference (až budou; do té doby „první svatby 2027 – staňte se referencí“ s bonusem).
- **Foto:** nádvoří nazdobené (mock-up ze skutečné fotky, ne AI), arkády, zahrada, apartmá, detail.
- **CTA:** „Nezávazně poptat termín 2027“ (sticky na mobilu); sekundární „Domluvit prohlídku“, „Stáhnout svatební brožuru (PDF)“.
- **Odkazy:** /svatby/prostory, /svatby/cenik-a-podminky, /gastronomie, /navsteva, /kontakt.
- **Schema:** BreadcrumbList, FAQPage, Place (s `maximumAttendeeCapacity`), Offer (od-cena) v rámci Service.
- **Konverze:** `generate_lead{type:svatba}` (primární), `file_download{brozura}`.

### `/firemni-akce`
- **Cílovka:** HR, office manažeři, agentury; B2B severozápadní Čechy + Praha.
- **KW:** firemní večírek na zámku, firemní akce zámek Ústecký kraj, netradiční místo pro konferenci, teambuilding zámek.
- **Title:** `Firemní akce na zámku Cítoliby | večírky, konference, teambuilding`
- **Description:** `Netradiční prostor pro firemní večírek, konferenci nebo teambuilding 60 minut od Prahy. Nádvoří pro stovky hostů, sály, zahrada, vlastní gastronomie. Nezávazná poptávka do 48 h.`
- **H1:** `Firemní akce na zámku Cítoliby`
- **Osnova:** H2 Typy akcí (večírek, konference, galavečer, teambuilding, produktová prezentace) · H2 Prostory a kapacity (tabulka: prostor, m², banket, divadlo, koktejl) · H2 Technika a zázemí · H2 Catering a program (divadlo, koncert na míru) · H2 Jak to probíhá (poptávka → nabídka 48 h → prohlídka → smlouva) · H2 Orientační cena (od … Kč / osoba, pronájem od …) · H2 Reference / partneři · H2 FAQ · H2 Poptávka.
- **CTA:** „Nezávazná poptávka“, „Stáhnout technický list prostor“.
- **Odkazy:** /pronajem-prostor, /prostory/*, /gastronomie, /program (firemní vstupenky), /kontakt.
- **Schema:** BreadcrumbList, FAQPage, Service + Place.
- **Konverze:** `generate_lead{type:event}`.

### `/program` a `/program/[slug]`
- **Cílovka:** kulturní publikum; prodej vstupenek.
- **KW:** program zámek Cítoliby, kulturní akce Louny, letní divadlo Louny, koncerty Louny, Zámecká Resonance program.
- **Title (hub):** `Program akcí – Zámek Cítoliby | divadlo, koncerty, slavnosti`
- **Title (detail):** `{Název akce} – {dd. mm. yyyy} | Zámek Cítoliby`
- **Description (detail):** `{Název}, {datum} {čas}, {scéna}. {1 věta o akci}. Vstupenky od {cena} Kč. Zámek Cítoliby u Loun.`
- **H1 (detail):** `{Název akce}`; H2 Termín a místo · H2 O představení/interpretovi · H2 Vstupenky (sektory, ceny, tlačítko) · H2 Praktické informace (příjezd, parkování, déšť) · H2 Další akce.
- **Životní cyklus:** před akcí = Event schema `EventScheduled`, Offer `InStock`/`SoldOut`; po akci = stránka zůstává (fotoreport, „Příště“), `eventStatus` beze změny, Offer odstraněn, odkaz na další ročník; zrušení = `EventCancelled`.
- **CTA:** „Koupit vstupenky“ (ticketing), před spuštěním „Hlídat předprodej“.
- **Schema:** Event (name, startDate, endDate, location Place s adresou, performer, organizer, offers s url/price/availability/validFrom, image, eventAttendanceMode Offline), BreadcrumbList, ItemList na hubu.
- **Konverze:** `ticket_purchase` (z ticketingu přes postMessage/GTM), `begin_checkout` (klik na koupit), `newsletter_signup{source:vstupenky}`.

### `/divadlo` (Zámecká Resonance)
- **KW:** letní divadlo Louny, divadlo pod širým nebem Ústecký kraj, Zámecká Resonance.
- **Title:** `Zámecká Resonance – letní divadlo na zámku Cítoliby | sezóna 2027`
- **Description:** `Letní divadelní scéna na nádvoří barokního zámku u Loun. Hlediště pro 900 diváků, 60 VIP míst v arkádách, komedie předních českých divadel. Hrajeme od května 2027. Předprodej.`
- **H1:** `Zámecká Resonance — letní divadlo pod širým nebem`
- **Osnova:** H2 Scéna, kterou navrhuje filmový architekt Jan Vlček · H2 Hlediště a sektory (plán sálu) · H2 Sezóna 2027 (program/„oznámíme“) · H2 VIP arkády a gastro balíčky · H2 Praktické (déšť, parkování, doprava z Loun/Prahy) · H2 Předprodej.
- **CTA:** „Chci předprodej jako první“ → po spuštění „Koupit vstupenky“.
- **Schema:** PerformingArtsTheater (Place) + Organization; eventy přes /program.

### `/gastronomie`
- **Title:** `Zámecká gastronomie Cítoliby | sezónní menu, slavnosti, vlastní výroba`
- **H1:** `Zámecká gastronomie`
- **Osnova:** kuchyně a lidé · kalendář sezónních chutí · gastro akce · rezervace / jak to funguje (po otevření) · pro svatby a firmy.
- **CTA:** „Rezervovat / Koupit vstupenku na gastro akci“, „Novinky z kuchyně“.
- **Schema:** Restaurant až po otevření (do té doby ne — neprodávat nedostupné).
- **Konverze:** `reservation`, `newsletter_signup{source:gastro}`.

### `/historie`, `/obnova-zamku`
- **Title:** `Historie zámku Cítoliby | Pachtové, hudba a baroko u Loun` / `Obnova zámku Cítoliby krok za krokem | Deník obnovy`
- **H1:** `Historie zámku Cítoliby` / `Obnova zámku: deník`
- **Osnova historie:** tvrz 1519 · zámek 1665 / přestavba 1717–1731 · Pachtové a hudební centrum · 20. století · 2002–2024 · Il Senso Vero (zdroje: NPÚ, Průzkumy památek 1995, Wikipedia).
- **Osnova obnovy:** timeline s milníky, fotoreporty, „co se právě děje“, jak pomoci / sdílet fotografie.
- **Schema:** Article/BlogPosting per kapitola, BreadcrumbList.
- **Konverze:** `newsletter_signup{source:novinky}`, čas na stránce.

### `/navsteva`, `/kontakt`
- **Title:** `Návštěva zámku Cítoliby | jak se dostat, parkování, otevírací doba` / `Kontakt – Zámek Cítoliby`
- **Obsah:** adresa (NAP shodný s GBP), telefon (klikací), e-mail, mapa (embed s consent), GPS, parkování, MHD z Loun, bezbariérovost, pravidla, provozní dny (jasně: co je dnes přístupné), tým (svatby / eventy / vstupenky kontakt), IČO/DIČ/sídlo CASTELLO CÍTOLIBY s.r.o.
- **Schema:** Organization + Place s `openingHoursSpecification` (jen reálné), ContactPoint.
- **Konverze:** `contact_click{phone|email|map}`.

## D5. Wireframy (textové, mobile-first)

```
HOMEPAGE (mobil)
┌──────────────────────────────┐
│ [erb] Zámek Cítoliby   [≡]   │  sticky header, CTA „Vstupenky“
├──────────────────────────────┤
│ HERO: skutečná fotografie    │
│ H1 Zámek Cítoliby — divadlo, │
│ svatby a gastronomie…        │
│ [Program a vstupenky]        │
│ [Poptat svatbu]              │
├──────────────────────────────┤
│ NEJBLIŽŠÍ AKCE               │
│ ▸ 31.10. Halloween na zámku  │
│ ▸ 28.11. Adventní otevření   │
│ ▸ 05/2027 Zámecká Resonance  │
│ [Celý program →]             │
├──────────────────────────────┤
│ CO U NÁS ZAŽIJETE (6 dlaždic)│
│ Divadlo · Koncerty · Svatby  │
│ Firemní akce · Gastro · Hist.│
├──────────────────────────────┤
│ SEZÓNA 2027 (fotka scény)    │
│ 900 míst · 60 VIP · od května│
│ [Chci předprodej jako první] │
├──────────────────────────────┤
│ SVATBY 2027 — zbývá 4 termíny│
│ od xx xxx Kč · [Poptat]      │
├──────────────────────────────┤
│ PROČ CÍTOLIBY (citát, foto)  │
├──────────────────────────────┤
│ DENÍK OBNOVY (3 poslední)    │
├──────────────────────────────┤
│ NOVINKY E-MAILEM [e-mail][→] │
│ ☐ zajímá mě: divadlo/svatby/ │
│   gastro/firemní             │
├──────────────────────────────┤
│ PATIČKA: adresa, tel, IČO,   │
│ mapa, odkazy, soc. sítě      │
└──────────────────────────────┘
 sticky bottom (mobil): [Vstupenky] [Poptat]

/SVATBY (mobil)
┌──────────────────────────────┐
│ Breadcrumb: Domů › Svatby    │
│ HERO foto nádvoří            │
│ H1 Svatba na zámku Cítoliby  │
│ 60 min od Prahy · 5 termínů  │
│ [Nezávazně poptat termín]    │
├──────────────────────────────┤
│ 3 ARGUMENTY (ikony)          │
├──────────────────────────────┤
│ PROSTORY (karusel, kapacity) │
├──────────────────────────────┤
│ JAK PROBÍHÁ DEN (timeline)   │
├──────────────────────────────┤
│ ORIENTAČNÍ CENY (tabulka)    │
├──────────────────────────────┤
│ VOLNÉ TERMÍNY 2027 (kalendář)│
├──────────────────────────────┤
│ FAQ (accordion, FAQPage)     │
├──────────────────────────────┤
│ POPTÁVKA (4 kroky: termín →  │
│ hosté+rozpočet → kontakt →   │
│ odesláno + co bude dál)      │
└──────────────────────────────┘
 sticky: [Poptat termín]

/PROGRAM/[AKCE]
┌──────────────────────────────┐
│ Breadcrumb › Program › Akce  │
│ Foto/plakát                  │
│ H1 Název akce                │
│ 📅 So 12. 6. 2027 20:00      │
│ 📍 Nádvoří, Zámek Cítoliby   │
│ 🎟 od 490 Kč   [Koupit]      │
├──────────────────────────────┤
│ O představení · Účinkující   │
├──────────────────────────────┤
│ Sektory a ceny (plán)        │
│ VIP arkády + gastro balíček  │
├──────────────────────────────┤
│ Praktické: déšť, parkování   │
├──────────────────────────────┤
│ Další akce (3)               │
└──────────────────────────────┘
 sticky: [Koupit vstupenky]
```
