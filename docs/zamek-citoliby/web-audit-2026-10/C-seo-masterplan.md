# C. SEO masterplan

## C1. Technický SEO audit (stav 8. 10. 2026)

| Oblast | Stav | Důkaz | Oprava |
|---|---|---|---|
| HTTPS, HSTS, www kanonizace | ✅ OK | 308 http→https, non-www→www; HSTS 2 roky | — |
| robots.txt | ❌ 404 | `curl /robots.txt` | `impl/robots.txt` (Next: `app/robots.ts`) |
| sitemap.xml | ❌ 404 | `curl /sitemap.xml` | `impl/sitemap.ts`; odeslat v GSC |
| Canonical | ❌ chybí | 0× `rel=canonical` | `metadataBase` + `alternates.canonical` (`impl/metadata.ts`) |
| Title | ⚠️ brandový, bez záměru | „Zámek Cítoliby \| Místo, kde příběhy pokračují“ | viz E (per stránka) |
| Meta description | ⚠️ obecná | bez produktu, bez lokality, bez CTA | viz E |
| H1 | ⚠️ „Zámek se probouzí“ | bez klíčového slova | H1 s produktem + místem na každé landing page |
| H2/H3 | ⚠️ | „Pět důvodů, proč přijet“, „Chci o všem vědět“ | nadpisy nesoucí záměr (svatba na zámku, letní divadlo…) |
| URL struktura | ❌ | jen `/` + kotvy | D: 12 landing pages |
| Interní prolinkování | ❌ | 0 interních odkazů (jen kotvy) | hub-and-spoke z homepage + patička |
| Duplicity / kanibalizace | ✅ n/a | 1 URL | hlídat při vzniku /divadlo vs /program |
| Strukturovaná data | ❌ 0 bloků JSON-LD | grep | `impl/jsonld-*.json` |
| Open Graph / Twitter | ✅ přítomno | OG image 1536×1152 (ilustrace, 300 kB) | nahradit fotografií, 1200×630, < 200 kB |
| Obrázky | ⚠️ | JPEG/PNG servírované přímo z `/images`, bez WebP/AVIF; erb PNG 85 kB 2× | `next/image` s remotePatterns, AVIF/WebP, `sizes` |
| JS rendering | ✅ obsah je v HTML (SSR/prerender) | `x-nextjs-prerender: 1` | držet SSR i pro nové stránky |
| JS payload | ⚠️ ~1,1 MB | chunk 551 kB | cíl < 300 kB; analyzovat bundle (`@next/bundle-analyzer`) |
| Core Web Vitals | ⚠️ jen lab | LCP 1,0–1,2 s, CLS 0 (US datacentrum, cache HIT) | po přestavbě měřit přes GSC CWV + web-vitals → GA4 |
| Mobil | ✅ responzivní; ⚠️ 14px, tap targety | lab | 16px base, 44px cíle |
| Indexace Seznam | ✅ homepage | search.seznam.cz | Seznam Webmaster: přidat web + sitemap |
| Indexace Google | ❓ neověřeno | bez přístupu k SERP | GSC → Pages; `site:` dotaz |
| GSC | ⚠️ property existuje, 0 dat | Windsor konektor | ověřit vlastnictví, odeslat sitemap, sledovat |
| Analytické skripty | ✅ consent-gated, Consent Mode v2 | 0 third-party před souhlasem | OK; doplnit konverze (J) |
| 404 | ⚠️ | správný status, anglický text | vlastní 404 |
| Bezpečnostní hlavičky | ✅ | HSTS, nosniff, referrer-policy, permissions-policy | doplnit CSP po stabilizaci GTM |
| Hreflang / EN | n/a | jen cs | EN verze až s poptávkou (Praha expats, firemní klienti) — P2 |

## C2. Strategie klíčových slov (100+ dotazů)

Objemy vyhledávání: **bez ověřeného zdroje** (nemáme přístup do Google Ads Keyword Planneru ani Skliku). Priorita je kvalifikovaná: Poptávka (odhad P1–P5), Konkurence (K1 nízká – K5 vysoká), Komerční hodnota (€1–€5), Sezónnost, Náročnost. Před nasazením kampaní ověřit v Keyword Planneru a Sklik návrhu klíčových slov a doplnit do `backlog.yaml` jako zdroj.

### Cluster 1 — Svatby (persona: snoubenci 27–38, Praha/Ústecký/Středočeský kraj; intent: komerční → transakční)

Landing page: `/svatby` (+ `/svatby/cenik-a-podminky`, `/svatby/prohlidka`). CTA: „Nezávazná poptávka termínu 2027“, sekundární „Domluvit prohlídku“. Konverze: `generate_lead{type:svatba}`.

| Dotaz | Poptávka | Konk. | Hodnota | Sezóna |
|---|---|---|---|---|
| svatba na zámku | P5 | K5 | €5 | X–III |
| svatba na zámku ceník | P3 | K3 | €5 | X–III |
| svatební místo Louny | P2 | K1 | €5 | celoročně |
| svatba Louny | P2 | K2 | €4 | |
| svatba Žatec zámek | P2 | K1 | €4 | |
| zámek svatba Ústecký kraj | P3 | K2 | €5 | |
| svatba na zámku Ústecký kraj | P3 | K2 | €5 | |
| svatební místo poblíž Prahy | P4 | K4 | €5 | |
| svatba na zámku u Prahy | P4 | K4 | €5 | |
| svatba na zámku s ubytováním | P3 | K3 | €5 | |
| svatba na zámku s cateringem | P2 | K2 | €5 | |
| svatba na zámku 100 hostů | P2 | K2 | €5 | |
| svatební obřad na nádvoří | P2 | K2 | €4 | |
| svatba v zámecké zahradě | P2 | K2 | €4 | |
| barokní zámek svatba | P2 | K2 | €4 | |
| soukromý zámek svatba | P2 | K2 | €5 | |
| exkluzivní svatba zámek | P2 | K3 | €5 | |
| svatba na zámku 2027 | P2 | K1 | €5 | |
| svatební termíny 2027 zámek | P2 | K1 | €5 | |
| svatba Lounsko | P1 | K1 | €4 | |
| svatební místo Most / Teplice / Kladno / Slaný / Rakovník / Litoměřice (6 variant) | P2 | K2 | €4 | |
| svatba v Čechách zámek Praha 1 hodina | P1 | K2 | €4 | |
| svatba na zámku zkušenosti | P2 | K3 | €3 | |
| svatba na zámku kolik stojí | P3 | K3 | €4 | |
| svatební koordinátor zámek | P1 | K2 | €4 | |
| wedding venue castle near Prague (EN) | P2 | K4 | €5 | |

### Cluster 2 — Divadlo a koncerty (persona: kulturní publikum 30–65, Louny–Praha; intent: informační → transakční)

Landing: `/program`, `/divadlo` (Zámecká Resonance), `/koncerty`, `/program/[akce]`. CTA: „Koupit vstupenky“ / „Chci předprodej jako první“. Konverze: `ticket_purchase`, `newsletter_signup{source:vstupenky}`.

| Dotaz | Poptávka | Konk. | Hodnota | Sezóna |
|---|---|---|---|---|
| letní divadlo Louny | P2 | K1 | €4 | IV–VIII |
| letní scéna Louny | P1 | K1 | €4 | |
| divadlo pod širým nebem | P4 | K3 | €4 | V–VIII |
| divadlo pod širým nebem Ústecký kraj | P2 | K1 | €4 | |
| letní divadlo Ústecký kraj | P2 | K1 | €4 | |
| letní divadlo u Prahy | P3 | K3 | €4 | |
| letní divadelní scéna 2027 | P2 | K1 | €4 | |
| divadlo Louny program | P3 | K2 | €3 | celoročně |
| kulturní akce Louny | P3 | K2 | €3 | |
| koncerty Louny | P3 | K2 | €3 | |
| koncerty Ústecký kraj | P3 | K3 | €3 | |
| koncert na zámku | P3 | K3 | €4 | V–IX |
| koncert pod širým nebem Ústecký kraj | P2 | K2 | €4 | |
| open air koncert Louny | P1 | K1 | €4 | |
| komorní koncert zámek | P1 | K1 | €3 | |
| Zámecká Resonance | P1 (brand) | K1 | €5 | |
| Zámecká Resonance program | brand | K1 | €5 | |
| Zámecká Resonance vstupenky | brand | K1 | €5 | |
| zámek Cítoliby divadlo | brand | K1 | €5 | |
| zámek Cítoliby koncert | brand | K1 | €5 | |
| zámek Cítoliby vstupenky | brand | K1 | €5 | |
| komedie divadlo venku léto | P2 | K3 | €3 | |
| divadlo Žatec program / divadlo Most program / Litoměřice (3) | P3 | K3 | €2 | |
| Vrchlického divadlo Louny program | P3 | K4 | €1 (jen obsah) | |
| kam na divadlo v létě | P3 | K3 | €3 | |
| letní shakespearovské slavnosti alternativa | P1 | K2 | €3 | |
| vstupenky divadlo online Louny | P2 | K2 | €4 | |
| dárkový poukaz divadlo | P3 | K3 | €4 | XI–XII |

### Cluster 3 — Firemní akce a pronájem prostor (persona: HR/office manager, event agentura, majitel firmy; B2B)

Landing: `/firemni-akce`, `/pronajem-prostor` (+ `/prostory/[nazev]`). CTA: „Nezávazná poptávka“, „Stáhnout technický list prostor“. Konverze: `generate_lead{type:event}`.

| Dotaz | Poptávka | Konk. | Hodnota | Sezóna |
|---|---|---|---|---|
| firemní večírek na zámku | P3 | K3 | €5 | IX–XI |
| vánoční večírek zámek | P3 | K3 | €5 | IX–XI |
| firemní akce zámek Ústecký kraj | P2 | K1 | €5 | |
| místo pro firemní akci Louny | P1 | K1 | €5 | |
| pronájem zámku | P3 | K3 | €5 | |
| pronájem zámku na akci | P2 | K3 | €5 | |
| pronájem prostor Louny | P2 | K2 | €4 | |
| pronájem sálu Louny | P2 | K2 | €3 | |
| pronájem nádvoří akce | P1 | K1 | €4 | |
| netradiční místo pro konferenci | P2 | K3 | €5 | |
| konference zámek Ústecký kraj | P1 | K1 | €5 | |
| teambuilding zámek | P2 | K3 | €4 | |
| teambuilding Ústecký kraj | P2 | K2 | €4 | |
| firemní akce u Prahy netradiční prostor | P2 | K3 | €5 | |
| oslava narozenin zámek pronájem | P2 | K2 | €4 | |
| soukromá oslava na zámku | P2 | K2 | €4 | |
| galavečer prostor pronájem | P1 | K2 | €4 | |
| natáčení lokace zámek (filmová lokace) | P1 | K2 | €3 | |
| prostor pro 200 lidí Louny / Žatec / Most | P1 | K1 | €4 | |
| eventová agentura Ústecký kraj | P1 | K2 | €2 (partnerství) | |

### Cluster 4 — Gastronomie a sezónní slavnosti (persona: rodiny, páry, místní 25–60)

Landing: `/gastronomie`, `/slavnosti`, `/program/[akce]`. CTA: „Rezervovat stůl / koupit vstupenku“, „Program slavností do e-mailu“. Konverze: `ticket_purchase`, `reservation`, `newsletter_signup{source:gastro}`.

| Dotaz | Poptávka | Konk. | Hodnota | Sezóna |
|---|---|---|---|---|
| zámecká restaurace Louny | P1 | K1 | €4 | |
| restaurace Cítoliby | P1 | K1 | €3 | |
| kam na oběd Louny okolí | P3 | K3 | €2 | |
| degustační menu Ústecký kraj | P1 | K1 | €4 | |
| rakousko-uherská kuchyně restaurace | P1 | K1 | €3 | |
| zámecké slavnosti | P3 | K3 | €3 | V–IX |
| zámecké slavnosti Ústecký kraj | P2 | K2 | €3 | |
| Halloween Louny | P2 | K1 | €3 | X |
| Halloween na zámku | P2 | K2 | €3 | X |
| Dušičky akce | P2 | K2 | €2 | X–XI |
| advent na zámku | P3 | K3 | €3 | XI–XII |
| adventní trhy Louny | P2 | K2 | €3 | XI–XII |
| vánoční trhy zámek Ústecký kraj | P2 | K2 | €3 | |
| svatomartinská husa Louny | P2 | K1 | €3 | XI |
| vinobraní zámek | P2 | K2 | €3 | IX |
| zabijačkové hody zámek | P1 | K1 | €3 | I–II |
| farmářské trhy Louny | P2 | K2 | €2 | |
| gastro festival Ústecký kraj | P1 | K2 | €3 | |

### Cluster 5 — Volný čas, výlety, historie (persona: rodiny, turisté, místní; intent: informační)

Landing: `/navsteva`, `/historie`, `/obnova-zamku`, blog. CTA: „Program akcí“, „Novinky z obnovy“. Konverze: `newsletter_signup{source:novinky}`, scroll/engagement.

| Dotaz | Poptávka | Konk. | Hodnota | Sezóna |
|---|---|---|---|---|
| zámek Cítoliby | brand P3 | K2 (Wikipedia, hrady.cz) | €4 | |
| Cítoliby zámek prohlídka | P2 | K1 | €3 | |
| Cítoliby zámek otevírací doba | P2 | K1 | €3 | |
| Cítoliby zámek historie | P2 | K2 | €2 | |
| Cítoliby | P3 | K3 | €2 | |
| co navštívit v Cítolibech | P1 | K1 | €2 | |
| kam o víkendu na Lounsku | P2 | K2 | €3 | |
| výlety kolem Loun | P3 | K3 | €2 | |
| výlet s dětmi Louny | P2 | K3 | €2 | |
| památky Lounsko | P2 | K2 | €2 | |
| zámky Ústecký kraj | P4 | K4 | €3 | |
| barokní zámky Čechy | P2 | K4 | €2 | |
| Pachtové z Rájova Cítoliby | P1 | K1 | €1 (autorita) | |
| cítolibská hudební škola / cítolibští mistři | P1 | K1 | €1 (autorita) | |
| Matyáš Braun Cítoliby sochy | P1 | K1 | €1 | |
| obnova zámku | P2 | K3 | €2 | |
| rekonstrukce památky příběh | P1 | K2 | €2 | |
| Jan Čáka zámek | brand | K1 | €2 | |
| ubytování na zámku Ústecký kraj | P2 | K3 | €4 (až bude) | |
| svatební apartmá zámek | P1 | K1 | €4 | |

Celkem: 112 dotazů (včetně 9 geografických variant). Každý cluster → 1 hub + 2–4 spoke stránky (D).

## C3. Konkurence (12 subjektů)

| Konkurent | Typ | Klíčová slova / stránky | Ceny, reference | Jak získává zákazníky | Výhoda | Slabina = naše příležitost |
|---|---|---|---|---|---|---|
| Státní zámek Krásný Dvůr (NPÚ) | NPÚ, 25 km | svatby, prohlídky, park; `/cs/svatby` | 3 svatební termíny 2026 (20. 6., 25. 7., 29. 8.), pravidla NKP | NPÚ síť, kudyznudy | značka NPÚ, park | kapacita 3 svatby/rok, úřední tón, žádný event/gastro |
| Státní zámek Stekník (NPÚ, UNESCO) | NPÚ, 20 km | svatby v zahradě, fotografování | ceník nenalezen | UNESCO PR, NPÚ | UNESCO | žádné večerní akce, žádný catering, minimální web |
| Zámek Libochovice (NPÚ) | NPÚ, 30 km | svatby „jako z pohádky“, divadlo na nádvoří (200 Kč), Hradozámecká noc | ceny na dotaz | NPÚ, denik.cz | park, historie | nepravidelný program, bez online ticketingu na vlastním webu |
| Zámek Ploskovice (NPÚ) | NPÚ, 50 km | svatby a pronájmy; `/svatby-a-pronajmy` | obřad park 2 000 Kč, sál 5 000 Kč (2024) | NPÚ | transparentní ceny | jen obřad, žádná hostina/produkce |
| Zámek Červený Hrádek (město Jirkov) | městský, 45 km | svatby, Zámecké pátky (jazz), hotel | termíny 2026 veřejně, louka 3 000 Kč, koordinátorka | web města, FB | hotel, koordinátorka, koncertní cyklus | web města, nízký brand, žádné divadlo |
| Nový Hrad Jimlín | obecní/NPÚ, 8 km | svatby v kapli, salonky, ubytování | ceník nenalezen | kudyznudy, Slevomat | nejbližší konkurent, ubytování | zastaralý web, žádný event marketing |
| Hrad Hněvín (Most) | městský, 40 km | „Hněvín žije hudbou“, Jazz Night, koncerty | vstupenky přes partnery | kalendář města, divadlo.net | pravidelný letní koncertní cyklus | restaurace-typ, ne divadlo, bez svateb premium |
| Zámek Děčín | městský, 80 km | Open Air Děčín (Chinaski), prohlídky | — | kultura365, město | velké koncerty | daleko, jiný segment |
| Zámek Liblice (AV ČR) | konferenční hotel, 75 km | svatby, ceník, konference, pokoje | obřad 10 500–12 500 Kč, altán 20 500 Kč, večeře 595 Kč/os | svatební katalogy, pragueweddings | hotel, veřejný ceník, reference | neosobní, instituce, bez kultury |
| Zámek Loučeň | soukromý, 90 km | svatby, balíčky, online rezervace termínu, labyrinty | balíčky 12 650–29 900 Kč, patro 25 000 Kč/so | silné SEO, balíčky, online rezervace | nejlepší svatební web v segmentu | daleko od Loun; vzor pro naši /svatby |
| Chateau Mcely | luxusní hotel, 100 km | Forbes „nejlepší svatební místo“, balíčky | exclusive 364 000 Kč/noc, intimate 74 300 Kč | PR, Forbes, Instagram | prestiž | cena 5–10× vyšší; my = dostupné premium |
| Chateau St. Havel (Praha) | hotel, 70 km | svatby Praha, recenze, menu ceník | pronájem ~49 000 Kč, menu 790–890 Kč | Google, katalogy, recenze | stránka recenzí, ceník menu | město, bez atmosféry venkova |
| Městské divadlo Žatec / Vrchlického divadlo Louny | kamenná divadla | program, online vstupenky (150 Kč letní kino) | — | Colosseum/GoOut | lokální publikum | zavřené sály, žádné open-air divadlo |

**Shrnutí:** V okruhu 50 km není nikdo, kdo by spojoval (a) prémiové svatby se servisem, (b) vlastní letní divadelní scénu s 900 místy, (c) gastronomii. NPÚ objekty mají autoritu, ale ne obchod. Soukromé prémiové zámky jsou 75–100 km daleko a 3–10× dražší.

## C4. SEO opportunity map (seřazeno podle hodnota × realizovatelnost)

| # | Příležitost | Poptávka | Konkurence | Hodnota | Sezónnost | Náročnost | Skóre |
|---|---|---|---|---|---|---|---|
| 1 | /svatby + regionální varianty (Louny, Ústecký kraj, u Prahy) | vysoká | nízká regionálně | nejvyšší | X–III | M | ★★★★★ |
| 2 | /program + detail akce (Event schema) — jediný open-air divadelní kalendář v kraji | střední | nízká | vysoká | III–VIII | M | ★★★★★ |
| 3 | /firemni-akce (vánoční večírky, teambuilding) | střední | nízká regionálně | vysoká | IX–XI | S | ★★★★☆ |
| 4 | Brand ochrana: „zámek Cítoliby“ (přebít hrady.cz/Wikipedia s „na prodej“) | střední | střední | vysoká (reputace) | celoročně | S | ★★★★☆ |
| 5 | Sezónní akce (Halloween, advent, svatomartinská husa) | střední | střední | střední | X–XII | S | ★★★☆☆ |
| 6 | /historie + /obnova-zamku (autorita, PR, AI citace) | nízká–střední | nízká | střední (nepřímá) | celoročně | M | ★★★☆☆ |
| 7 | /navsteva (otevírací doba, jak se dostat, parkování) | střední | nízká | střední | V–IX | S | ★★★☆☆ |
| 8 | Výlety/„kam o víkendu“ obsah (blog) | střední | střední | nízká | V–IX | M | ★★☆☆☆ |
| 9 | EN verze pro svatby a firemní klienty | nízká | vysoká | vysoká/lead | — | L | ★★☆☆☆ (2027 H2) |

## C5. Plán budování autority (bez nákupu odkazů)

1. **Oprava entit** (týden 1–2): Wikipedia „Cítoliby (zámek)“ (aktualizovat vlastníka, stav obnovy, zdroje = tisk), Wikidata (oficiální web, obrázek), hrady.cz (vlastník, přístupnost, web), kudyznudy.cz (nový profil aktivity + akce), turistika.cz, kultura.cz, Mapy.cz, Firmy.cz, GBP.
2. **Lokální média**: Žatecký/Lounský deník, Rozhlas Sever, e-zatecko.cz, Lounský kraj — tisková zpráva „Zámek Cítoliby po 20 letech ožívá: sezóna 2027“ + exkluzivní prohlídka pro novináře. Cíl: 5 odkazujících článků do 90 dnů.
3. **Turistické organizace**: Destinační agentura Dolní Poohří (dolnipoohri.cz – registrují pořadatele akcí), Ústecký kraj „Brána do Čech“, Město Louny (kalendář akcí, Vrchlického divadlo), Městys Cítoliby (web obce – odkaz na zámek).
4. **Kulturní partneři**: divadla, která budou hostovat (jejich weby odkazují na místo konání), ticketing (GoOut profil místa = odkaz + traffic), kulturnimapa.cz, kultura365.cz, goout.net, divadlo.net.
5. **Svatební katalogy** (bezplatné/registrace): svatebnimisto.cz, svatba.cz, snubak.cz, svatebniatlas.cz, mojeparty.cz, svatebni-katalog.cz — konzistentní NAP a odkaz.
6. **Eventové katalogy**: meatspace.cz, firemniakce.cz, konferencniprostory.info.
7. **Digitální PR obsah**: „Deník obnovy“ (měsíční fotoreport), historická série (Pachtové, cítolibská hudební škola, Braun), rozhovor s architektem scény. Originální fotografie = přirozeně sdílený a citovaný materiál.
8. **Nikdy**: PBN, nákup odkazů, falešné lokální stránky, falešné recenze.
