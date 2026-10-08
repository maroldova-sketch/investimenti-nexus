# A. Executive summary — Zámek Cítoliby, audit webu a digitálního obchodu

**Datum auditu:** 8. 10. 2026 · **Web:** https://www.zamek-citoliby.cz · **Horizont:** sezóna 2027, strategie do 2030
**Důkazy:** `data/audit-evidence.json`, screenshoty v `data/`. Ověřená fakta = F, hypotéza = H.

## Závěr jednou větou

Web je hezká vizitka, ale **není obchodní nástroj**: jedna stránka bez podstránek, bez kontaktu, bez cen, bez fotek, bez programu, nulová organická viditelnost a internet o zámku stále říká „zanedbaný, na prodej, nepřístupný“.

## Co dnes brání prodeji (ověřeno)

1. **Jediná stránka, žádné vstupní URL** (F). Všechny komerční cesty (/svatby, /program, /kontakt…) vrací 404. Google nemá co zaindexovat k dotazům „svatba na zámku Louny“ nebo „letní divadlo Ústecký kraj“. Title ani nadpisy neobsahují jediné komerční klíčové slovo.
2. **Nulová organická stopa** (F). Search Console (sc-domain) vrací 0 řádků za 30 dní, 3 měsíce i 12 měsíců; GA4 má data jen od 7. 10. 2026 (5 relací). Chybí robots.txt, sitemap.xml, canonical, strukturovaná data.
3. **Internet mluví proti nám** (F). hrady.cz, Wikipedia, Deník: „nepřístupný veřejnosti, zanedbaný, na prodej za cenu pražského bytu“. AI vyhledávání na dotaz „Co navštívit v Cítolibech“ odpovídá přesně tím. Firmy.cz záznam neexistuje, Google Business Profile neověřen.
4. **Chybí základní důvěra** (F). Na webu není telefon, adresa, mapa, IČO, fotografie skutečného zámku (hero je kreslená ilustrace), reference, ceny ani orientační podmínky. Položka „Fotografie“ v menu vede na formulář pro sběr starých snímků, ne na galerii.
5. **Konverzní cesty se slévají do jednoho e-mailu** (F). Tři CTA „Chci vědět víc“ (Divadlo, Hudba, Gastronomie) vedou na stejný newsletter. Poptávka svatby a eventu je identický formulář bez kvalifikace (rozpočet, typ akce, firma). Ecomail má 57 potvrzených kontaktů v jednom listu bez segmentace a 0 odeslaných kampaní.
6. **Měření bez konverzí** (F/H). GTM, GA4, Meta Pixel i Ecomail tracker jsou nasazeny správně a consent-gated (dobře), ale dataLayer neobsahuje žádné vlastní události; odeslání formulářů se zřejmě neměří jako konverze (H – ověřit v GTM kontejneru).
7. **Technický dluh v0.app šablony** (F). 1,1 MB JavaScriptu na jednostránkový web (jeden chunk 551 kB), 14px základní písmo, zlatý text na slonové kosti ~3,85:1 (pod WCAG AA), cookie lišta překrývá CTA.

## Hlavní příležitosti

- **Region nemá premiového hráče.** Konkurence jsou státní zámky NPÚ (Krásný Dvůr, Stekník, Libochovice, Ploskovice) s 3 svatebními termíny ročně, úředním jazykem a bez obchodního webu, nebo městské objekty (Červený Hrádek). Prémiové svatební zámky (Liblice, Loučeň, Mcely) jsou 60–90 min od Loun a 3–10× dražší. Pozice „prémiový soukromý zámek 60 min od Prahy, s vlastním divadlem a gastronomií“ je volná.
- **Letní divadlo 900 míst nemá v Ústeckém kraji obdobu.** Nejbližší srovnatelné letní scény jsou v Praze. Dotazy „letní divadlo“, „divadlo pod širým nebem“, „kam o víkendu Lounsko“ nikdo v kraji systematicky nepokrývá.
- **Vlastní databáze roste bez reklamy** (57 kontaktů za 30 dní). S programem a předprodejem je to základ pro prodej sezóny 2027 bez placených médií.
- **Příběh obnovy** je unikátní obsah, který NPÚ ani hotely nemají, a přímo opravuje negativní narativ „zanedbaný zámek“.

## Očekávaný přínos (cíle, ne měření)

| Oblast | Dnes (F) | Cíl 30. 6. 2027 (cíl) |
|---|---|---|
| Indexované komerční stránky | 0 | 12+ |
| Nebrandové organické kliky / měsíc | 0 | 1 500+ |
| Kvalifikované svatební poptávky / měsíc | neměřeno | 8–15 (sezóna leden–duben) |
| Poptávky firemních akcí / měsíc | neměřeno | 4–8 |
| E-mailová databáze | 57 | 3 000+ segmentovaných |
| Prodané vstupenky sezóna 2027 | 0 (předprodej neběží) | viz finanční model G (scénáře 8–16 tis.) |

## Pět rozhodnutí, která doporučuji teď

1. **Přestavět web na vícestránkový Next.js s CMS** (program, svatby, firemní akce, gastronomie, historie/obnova, kontakt) do 60 dnů. Ne redesign, ale stavba obchodní platformy. Zachovat identitu (modř, slonová kost, zlato, erb).
2. **Do 7 dnů opravit technické základy** na stávajícím webu: robots, sitemap, canonical, JSON-LD, kontakt s telefonem a adresou, fotografie skutečného zámku, měření konverzí.
3. **Vzít si zpět narativ**: Google Business Profile, Firmy.cz, Wikipedia, hrady.cz, kudyznudy — aktualizovat fakta (nový majitel, obnova, sezóna 2027). Jedna tisková zpráva pro Deník a Rozhlas Sever.
4. **Vybrat ticketing do 30 dnů** (GoOut nebo Enigoo; kritéria v H) a spustit předprodej sezóny 2027 nejpozději v prosinci 2026 s early-bird pro e-mailovou databázi.
5. **Rozpočet**: růstová varianta 95 tis. Kč/měsíc (web + obsah + reklama) do června 2027, podmínky návratnosti v G.

## Co nebylo možné ověřit

Google index a Core Web Vitals z reálných uživatelů (web nemá CrUX data), obsah GTM kontejneru, stav Google Business Profile, Google Ads/Sklik účty, obsah Ecomail kampaní, zdrojový kód webu (v0.app projekt není v dostupném repozitáři). Windsor.ai konektor je v trial režimu – čísla z GA4/GSC/Meta jsou orientační, potvrdit v nativních rozhraních.
