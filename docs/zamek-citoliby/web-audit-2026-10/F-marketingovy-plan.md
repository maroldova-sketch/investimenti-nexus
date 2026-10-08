# F. Marketingový plán

## F1. Conversion Rate Optimization

### Konverzní cesty a požadavky
| Cesta | Kroky | Co musí web umět | Primární metrika |
|---|---|---|---|
| Svatba | návštěva → inspirace (/svatby, galerie) → nabídka (ceny, termíny) → poptávka (4 kroky) → prohlídka (kalendář) → rezervace (záloha) | od-ceny, kalendář 5 termínů, vícekrokový formulář, auto-odpověď, CRM záznam | kvalifikovaná poptávka (rozpočet + termín + hosté vyplněno) |
| Divadlo | vyhledání (program, Google) → detail → výběr míst → nákup → upsell (VIP, gastro, parkování) → opakovaná návštěva | Event stránky, ticketing s plánem sálu, UTM, e-mail po akci | purchase + ARPU (vstupenka + doplňky) |
| Firemní event | landing → reference a parametry → technický list → poptávka → nabídka 48 h | tabulky kapacit, PDF, B2B formulář, SLA | poptávka s firmou + rozpočtem |
| Newsletter | návštěva → kontextové přihlášení → DOI → tag zájmu → nabídka | formulář s výběrem zájmu, Ecomail tagy, welcome série | DOI potvrzení, CTR nabídky |

### Vyhodnocení prvků
| Prvek | Přínos | Verdikt |
|---|---|---|
| Sticky CTA na mobilu | mobil = většina návštěv z FB/IG; dnes CTA zmizí po scrollu | **Ano** (Vstupenky + Poptat) |
| Kratší formuláře | svatební poptávka dnes 7 polí; vícekrokový s progresí zvyšuje dokončení a kvalitu | **Ano, vícekrokový** (ne kratší, ale rozdělený) |
| Orientační ceny včas | konkurence (Liblice, Loučeň, Ploskovice) ceny má; bez nich poptávky nekvalifikované | **Ano** („od“ ceny) |
| Ukázky prostor a kapacit | dnes 0 fotek, 0 čísel | **Kritické** |
| Reference / sociální důkaz | dnes 0; sbírat od první akce; do té doby média, partneři, „první svatby 2027“ | **Ano, postupně** |
| Programový kalendář | bez něj nelze prodat vstupenku | **Kritické** |
| VIP a gastro balíčky | zvyšují ARPU o 30–80 % (předpoklad k testu) | **Ano, od spuštění ticketingu** |
| Doporučení souvisejících akcí | cross-sell na detailu akce + v potvrzovacím e-mailu | **Ano** |
| Automatické připomínky/follow-upy | svatby: 24 h / 3 dny / 10 dní; vstupenky: 48 h před akcí; po akci: recenze | **Ano** (Ecomail automatizace + interní systém) |

### 10 A/B testů (po nasazení měření; minimální vzorek ~200 konverzí na variantu, jinak vyhodnocovat jako sekvenční test)
| # | Hypotéza | Varianta A / B | Metrika |
|---|---|---|---|
| 1 | Zobrazení od-ceny na /svatby zvýší podíl kvalifikovaných poptávek | bez ceny / s cenou „od“ | kvalifikované poptávky / návštěvy |
| 2 | Vícekrokový formulář zvýší dokončení | 1 krok / 4 kroky | dokončení formuláře |
| 3 | Sticky CTA „Koupit vstupenky“ na mobilu zvýší begin_checkout | bez / s | begin_checkout / relace (mobil) |
| 4 | Fotografie skutečného zámku v hero zvýší engagement a CTA click oproti ilustraci | ilustrace / fotografie | cta_click, scroll 50 %, bounce |
| 5 | Výběr zájmu při přihlášení k newsletteru nesníží počet přihlášení, ale zvýší CTR kampaní | bez výběru / s výběrem | signup rate; CTR 1. kampaně |
| 6 | Kalendář volných termínů 2027 (urgence „zbývá 3“) zvýší poptávky | bez / s | generate_lead svatba |
| 7 | Gastro balíček nabídnutý v košíku ticketingu zvýší ARPU | bez / s | ARPU, podíl upsellu |
| 8 | Title „Svatba na zámku u Loun, 60 min od Prahy“ vs „Svatba na zámku Cítoliby“ zvýší CTR v SERP | A/B přes GSC v čase (2× 4 týdny) | CTR dotazů „svatba na zámku“ |
| 9 | Early-bird pro databázi (72 h před veřejným předprodejem) zvýší první týden prodeje | kontrolní segment bez early-bird / s | tržby den 1–7, konverze e-mailu |
| 10 | Blok „Co je dnes hotové, co ne“ (upřímnost o obnově) zvýší důvěru a poptávky | bez / s | generate_lead, čas na stránce |

## F2. Lokální SEO a Google Business Profile

Stav: Firmy.cz bez záznamu (F), GBP neověřeno (bez přístupu), NAP na webu neúplné (F: jen e-mail).

Plán (vše pravdivé, bez falešných lokalit):
1. **GBP**: nárokovat/založit „Zámek Cítoliby“. Primární kategorie: *Zámek* (Castle); sekundární: *Svatební místo*, *Místo konání akcí*, *Divadlo pod širým nebem* (až od 2027), *Turistická atrakce*. Adresa přesná (Zámecká …, 439 02 Cítoliby), telefon, web, popis s produkty, atributy. Provozní doba: **jen reálná** — dnes „otevřeno při akcích / na objednání“ → nastavit „Otevírací doba není k dispozici“ + „Zvláštní otevírací doba“ u akcí; neuvádět fiktivní denní hodiny.
2. **Fotografie**: 20+ skutečných (exteriér, nádvoří, arkády, obnova, tým), logo = schválený erb; měsíčně doplnit.
3. **Příspěvky a události**: každá akce jako GBP Event s odkazem na /program/[slug]; měsíční aktualizace z obnovy.
4. **Recenze**: QR kód + odkaz po každé akci / svatbě / firemní akci; cíl 25 reálných recenzí do konce 2027; odpověď do 48 h, i na negativní. Nikdy nenakupovat.
5. **Citace a konzistence NAP**: Firmy.cz, Mapy.cz, Kudyznudy, Dolní Poohří, Brána do Čech, obec Cítoliby, hrady.cz, turistika.cz, svatební a eventové katalogy — stejný název, adresa, telefon, web; vést v `marketing/NAP.md` (již existuje na Macu — použít jako zdroj pravdy).
6. **Návaznost**: GBP „Rezervace“/„Vstupenky“ link → ticketing s UTM `utm_source=google&utm_medium=gbp`; „Nabídka“ → /svatby.
7. **Web**: /kontakt a /navsteva s Place JSON-LD, mapa, GPS; patička s NAP na každé stránce.
8. **Seznam**: Firmy.cz profil + Seznam Webmaster + sitemap.

## F3. AI vyhledávání (GEO/AEO)

Stav (proxy přes webové vyhledávání, F): na dotazy o svatbě u Loun, firemním večírku v kraji a „co navštívit v Cítolibech“ zámek buď chybí, nebo je citován jako „na prodej, nepřístupný“ (hrady.cz, Wikipedia, Deník 1/2025). Zámecká Resonance má nulovou viditelnost.

Opatření (podle doporučení Google: kvalitní, faktický, dostupný obsah; žádné „AI značkování“):
1. **Opravit zdrojové entity**, ze kterých AI čerpá: Wikipedia (s citacemi na tisk), Wikidata, hrady.cz, kudyznudy. Bez toho budou AI odpovědi dál citovat prodej.
2. **Faktické stránky se strukturou otázka–odpověď**: /navsteva (otevírací doba, jak se dostat), /svatby FAQ, /firemni-akce FAQ, /historie s daty a jmény, /divadlo s parametry (900 míst, 60 VIP, architekt). Krátké, přímé věty v prvních odstavcích.
3. **Konzistentní entita**: Organization + Place JSON-LD se `sameAs` (Wikipedia, Wikidata, FB, IG, GBP), stejný název všude.
4. **Citovatelnost**: tisk (Deník, Rozhlas Sever), regionální turistické weby, kulturní kalendáře → AI systémy preferují vícezdrojově potvrzené entity.
5. **Technicky**: obsah v HTML (ne za JS), rychlé načtení, robots povolující běžné crawlery; žádné blokování AI crawlerů, pokud nechceme (rozhodnutí: povolit).
6. **Monitoring**: měsíčně 10 testovacích dotazů v Google AI Mode, ChatGPT, Perplexity, Seznam; zapisovat do dashboardu (J) jako kvalitativní KPI.

## F4. Obsahová a PR strategie

Pilíře → obchodní účel:
| Pilíř | Formát | Účel | Konverze |
|---|---|---|---|
| Historie zámku a Cítolib | kapitoly /historie, 1×/měsíc | autorita, AI citace, oprava narativu | newsletter novinky |
| Obnova krok za krokem | „Deník obnovy“ fotoreport 2×/měsíc (web + IG + FB + e-mail) | důvěra, PR, komunita | newsletter, sdílení |
| Lidé a osobnosti | rozhovory (architekt Jan Vlček, kuchař, řemeslníci, pamětníci) 1×/měsíc | prestiž, média | — |
| Zámecká Resonance a účinkující | profily divadel/představení, zákulisí stavby scény | prodej vstupenek | ticket_purchase |
| Svatby a inspirace | prostory, „jak probíhá den“, reálné svatby 2027 (se souhlasem) | poptávky | generate_lead svatba |
| Gastronomie a tradice | sezónní kalendář chutí, recept měsíce, svatomartinská husa, zabijačka | gastro akce | reservation/ticket |
| Regionální kultura a cestovní ruch | „Kam o víkendu na Lounsku“ – jen s originální hodnotou (naše tipy, partneři) | návštěvnost, partneři | newsletter |
| Příběhy návštěvníků | sdílené fotografie z /pamet-mista (se souhlasem), první diváci | komunita, UGC | — |

### Publikační kalendář 90 dní (říjen–prosinec 2026)
| Týden | Web | E-mail | Sociální sítě | PR |
|---|---|---|---|---|
| 41 (6.–12. 10.) | /kontakt, /navsteva, galerie 20 fotek | welcome série (3 e-maily) nasazena | 3× IG/FB: „fotíme zámek“, erb, tým | příprava TZ |
| 42 | /svatby + FAQ, /firemni-akce | — | 3× (svatby: arkády, zahrada, apartmá) | TZ „Zámek ožívá, sezóna 2027“ → Deník, Rozhlas Sever, e-zatecko |
| 43 | /program s Halloween/Dušičky (pokud potvrzeno), /historie kap. 1 (tvrz → zámek 1665) | #1 „Deník obnovy“ + oznámení svateb 2027 | 3× (historie, obnova) | oprava Wikipedia/hrady.cz/kudyznudy |
| 44 | /obnova-zamku timeline, Deník #2 | — | Halloween/Dušičky akce (pokud) | — |
| 45 | /divadlo plná verze + plán hlediště | #2 „Zámecká Resonance: jak vzniká scéna“ (rozhovor Vlček) | 3× zákulisí scény | Rozhovor pro Lounský kraj / Rozhlas |
| 46 | /gastronomie (připravujeme), svatomartinské téma | — | 3× gastro | svatební katalogy registrace |
| 47 | /historie kap. 2 (Pachtové, hudební škola), Deník #3 | #3 „Advent na zámku“ (pokud akce) | advent teaser | — |
| 48 | /slavnosti, adventní akce detail | advent pozvánka | 3× | eventové katalogy |
| 49 | /pronajem-prostor + technické listy | #4 „Firemní večírky 2027 — rezervujte brzy“ (B2B segment) | 3× | LinkedIn Jan Čáka: článek |
| 50 | Program sezóny 2027 (část) | **#5 Early-bird předprodej pro databázi** (72 h před veřejným) | countdown | TZ „Program Zámecké Resonance“ |
| 51 | /program s prvními tituly 2027, dárkové poukazy | #6 „Dárek pod stromeček: vstupenky 2027“ | 3× | — |
| 52 | Deník #4 „Rok 2026 na zámku“ | PF + shrnutí | retrospektiva | — |
| 1–2/2027 | /historie kap. 3, svatby „zbývá X termínů“ | #7 svatební inspirace (segment svatby) | 3×/týden | svatební veletrhy (Praha) |

### Roční tematický rámec 2027
- **Leden–únor:** svatební sezóna poptávek (inspirace, prohlídky), zabijačka, program sezóny kompletní, předprodej.
- **Březen–duben:** stavba scény (deník), kampaň vstupenky, Velikonoce, otevření zahrady (pokud).
- **Květen–srpen:** Zámecká Resonance (každé představení = obsah před/po), koncerty, gastro večery, pouť sv. Jakuba (červenec).
- **Září–říjen:** firemní vánoční večírky (B2B kampaň od září), vinobraní, Halloween, Dušičky, svatby mimo sezónu.
- **Listopad–prosinec:** svatomartinská husa, advent, dárkové poukazy, early-bird 2028.

### Partnerství
Město Louny (kalendář, Vrchlického divadlo – spolupráce ne konkurence), Městys Cítoliby, Destinační agentura Dolní Poohří, Ústecký kraj / Brána do Čech, Žatec (UNESCO chmel – balíčky výlet + divadlo), hostující divadla, Rozhlas Sever, Deník, e-zatecko, regionální pivovary/vinaři (gastro), hotely v Lounech a Žatci (ubytování pro svatby a diváky z Prahy), svatební agentury Praha, event agentury (Dream PRO Ústí a pražské).

## F5. Placený marketing

Rozdělení: **brand** (Zámek Cítoliby, Zámecká Resonance — levné, ochrana, vždy zapnuto) vs **nebrand** (svatba na zámku…, letní divadlo…, firemní večírek…). Remarketing jen se souhlasem (Consent Mode v2 již nasazen; Meta Pixel po souhlasu; doplnit Meta CAPI s `event_id` deduplikací).

| Kanál | Publikum | Produkt / sdělení | Kreativa | Měřená konverze | Cíl CPA/CPL (předpoklad k testu) | Optimalizace |
|---|---|---|---|---|---|---|
| Google Ads Search – brand | hledající název | ochrana, sitelinks (Program, Svatby, Firemní, Kontakt) | RSA | všechny | CPC < 3 Kč | týdně negativní KW |
| Google Ads Search – svatby | „svatba na zámku“ + kraje, Praha; 25–40 | 5 termínů 2027, 60 min od Prahy | RSA + obrázky, callouts „od xx Kč“ | generate_lead svatba | CPL 600–1 200 Kč (kvalifikovaný) | tCPA po 30 konverzích, hodnota leadu |
| Google Ads Search – firemní | B2B dotazy, zář–lis | vánoční večírek, konference | RSA | generate_lead event | CPL 800–1 500 Kč | sezónní rozpočet |
| Google Ads Search – divadlo/koncerty | „letní divadlo“, „divadlo pod širým nebem“, Louny/Praha; interpret + město | konkrétní představení | RSA per akce | purchase (hodnota) | ROAS ≥ 4 | per-event kampaně, pauza po vyprodání |
| Performance Max / Demand Gen | lookalike databáze, zájmy divadlo/kultura, 50 km Louny + Praha | předprodej, VIP | video/foto | purchase | ROAS ≥ 3 | od března 2027 |
| Sklik – vyhledávání | starší publikum, regionální (Seznam silný v Ústeckém kraji) | stejná struktura (brand, svatby, divadlo) | textové + rozšíření | lead/purchase | CPL svatba < 1 000 Kč, ROAS divadlo ≥ 3 | týdně |
| Sklik – obsahová síť / retargeting | návštěvníci /program, /svatby | připomínka akce, termíny | bannery | purchase/lead | CPM test | frekvence ≤ 3 |
| Meta Ads – prospecting | 25–55, 60 km Louny + Praha, zájmy kultura/svatba | Deník obnovy (video), svatby, předprodej | video 15 s, karusel fotek | lead, purchase, signup | CPL svatba < 900 Kč, ticket CPA < 120 Kč | kreativa týdně, Advantage+ |
| Meta Ads – remarketing + databáze | web návštěvníci (souhlas), Ecomail custom audience | konkrétní akce, poslední místa | dynamické | purchase | ROAS ≥ 5 | — |
| Meta Lead Ads | svatby (formulář v appce, synchro do Ecomail/CRM) | „Chci termín 2027“ | obrázek + formulář | lead | CPL < 500 Kč (nižší kvalita — kvalifikovat telefonem) | — |
| E-mail (Ecomail) | vlastní databáze podle tagů | early-bird, program, svatby, B2B | šablona v identitě | purchase/lead | ROI nejvyšší, náklad fixní | A/B předmětů |
| LinkedIn (organicky + 2 boosty) | HR/office Ústecký + Praha | firemní akce | článek J. Čáky | lead event | — | zář–lis |

### Rozpočtové varianty (měsíčně, média bez agentury; kreativa a správa zvlášť v G)
| Položka | Úsporná | Růstová (doporučeno) | Ambiciózní |
|---|---|---|---|
| Google Ads (brand + svatby + firemní + divadlo) | 8 000 | 25 000 | 60 000 |
| Sklik | 3 000 | 8 000 | 15 000 |
| Meta Ads | 6 000 | 20 000 | 50 000 |
| Remarketing (v rámci) | — | — | — |
| Médiá celkem / měsíc | **17 000** | **53 000** | **125 000** |
| Sezónní špička (III–V 2027, předprodej) | +15 000 | +40 000 | +100 000 |

### Předprodej sezóny 2027 — plán
1. Prosinec: program (aspoň 50 %) + ceník sektorů + ticketing live; early-bird 72 h jen pro databázi (sleva nebo bonus, ne dumping).
2. Prosinec–leden: dárkové poukazy (vánoční kampaň Meta + e-mail).
3. Březen–duben: hlavní kampaň (Google, Sklik, Meta, PR, outdoor Louny/Žatec/Praha 6 — mimo scope webu).
4. Každé představení: vlastní URL + Event schema + per-event kampaň + remarketing 14 dní před.
5. Po každé akci: e-mail s recenzí a nabídkou dalších 2 akcí.

## F6. CRM, e-mail, automatizace

Stav (F): Ecomail list 2 „Zámek Cítoliby – novinky a předprodej“, 57 potvrzených, 2 čekající, 0 kampaní, doména odesílatele validní, formuláře z webu funkční (server action → Ecomail). Meta Lead Ads účet existuje (konektor facebook_leads). GA4 + GTM + Pixel nasazeny. Interní platforma citoliby.investimenti.cz / MAXINA — neauditováno (bez přístupu k aplikaci; repo `citoliby-dashboard` na Macu existuje).

Jednotný funnel (zdroj pravdy = interní systém, Ecomail = odesílání):
```
web formulář / Meta Lead / ticketing / GBP →  interní CRM (lead: typ, zdroj, UTM, stav, hodnota)
                                            →  Ecomail kontakt + tagy (zajem:divadlo|koncerty|svatby|gastro|eventy|komunita, stav:lead|zakaznik, zdroj)
GA4 (anonymní) ← GTM ← web události; ticketing purchase s transaction_id; Meta CAPI s event_id = GTM event_id
```
Segmenty: divadlo, koncerty, svatby (lead / zákazník), gastronomie, firemní (B2B), komunita (historie/pamětníci), dárkové poukazy.

Automatizace (vše jen se souhlasem pro daný účel; DOI zachovat):
1. **Welcome série** (novinky): D0 příběh + co čekat; D3 Deník obnovy; D10 „Sezóna 2027“ + výběr zájmu (tag).
2. **Svatební lead**: okamžitá potvrzovací zpráva; D1 telefonát (úkol v CRM); D3 e-mail „prostory + FAQ“; D10 „zbývá X termínů“; D30 pokud bez odpovědi → uzavřít s tagem.
3. **Firemní lead**: potvrzení; nabídka do 48 h (úkol); D7 follow-up; D21 poslední.
4. **Vstupenky**: potvrzení (ticketing); D-2 připomínka s praktickými info; D+1 „Jak se vám líbilo“ + recenze + 2 další akce; sezónní „opakovaný divák“ sleva.
5. **Early-bird**: segment databáze 72 h před veřejným předprodejem.
6. **Reaktivace**: 6 měsíců bez otevření → 1 e-mail, pak útlum.
GDPR: účel „poptávka“ ≠ „marketing“ — marketingový souhlas vždy samostatný checkbox; kontakty z jiných firem holdingu (VZC, KERA-DENS…) se **nepřevádějí**; evidence souhlasu (čas, zdroj, text) v Ecomailu i CRM; odhlášení v každém e-mailu; retence leadů bez konverze 24 měsíců.
