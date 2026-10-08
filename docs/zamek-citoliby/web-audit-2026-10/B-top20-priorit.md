# B. Top 20 priorit

Legenda: Dopad 1–5 (5 = přímý vliv na tržby), Náročnost S/M/L (S < 1 den, M 1–5 dní, L > 5 dní), Priorita P0 (do 7 dnů), P1 (do 30 dnů), P2 (do 90 dnů). Důkaz: F = ověřeno měřením/kódem, H = hypotéza.

| # | Problém | Důkaz | Doporučení | Náročnost | Dopad | Priorita | Role |
|---|---|---|---|---|---|---|---|
| 1 | Web je jedna stránka, komerční URL vrací 404 | F: /svatby, /program, /kontakt, /divadlo = 404; nav jen kotvy | Nová IA s 12 landing pages (D), postupně nasazovat: /svatby, /firemni-akce, /program, /kontakt jako první | L | 5 | P1 | Web dev + CMO |
| 2 | Nulová organická viditelnost | F: GSC 0 řádků 12 m; title/H1 bez klíčových slov | Přepsat title/description/H1, publikovat robots+sitemap, odeslat do GSC, JSON-LD (impl/) | S | 5 | P0 | SEO |
| 3 | Chybí kontakt (telefon, adresa, mapa, IČO) | F: na stránce jen mailto | Přidat kontaktní blok + stránku /kontakt s mapou, NAP shodný s GBP; IČO/sídlo do patičky | S | 5 | P0 | Web dev |
| 4 | Hero je ilustrace, žádná fotogalerie | F: alt „Ilustrace čelního pohledu…“; „Fotografie“ v menu = formulář | Nafotit zámek (exteriér, nádvoří, arkády, sál, zahrada, detaily obnovy) a nasadit galerii; ilustraci nechat jen jako brand prvek | M | 5 | P0 | Marketing |
| 5 | Internet říká „na prodej, zanedbaný, nepřístupný“ | F: hrady.cz, Wikipedia, Deník 1/2025; AI odpovědi | Opravit profily (hrady.cz, Wikipedia, kudyznudy, turistika.cz), tisková zpráva, GBP + Firmy.cz | M | 5 | P0 | PR + lokální SEO |
| 6 | Google Business Profile nepotvrzen, Firmy.cz chybí | F: Firmy.cz bez záznamu; GBP neověřeno | Založit/ověřit GBP (kategorie: Zámek + Svatební místo + Místo konání akcí), Firmy.cz, Mapy.cz, Kudyznudy | S | 4 | P0 | Lokální SEO |
| 7 | Konverze se neměří | F: dataLayer bez custom událostí; H: GTM bez konverzí | Měřicí plán (J): generate_lead(type), newsletter_signup(source), cta_click, outbound; GA4 key events; Meta CAPI s event_id | M | 4 | P0 | Analytik |
| 8 | Tři různé zájmy (divadlo, hudba, gastro) → jeden newsletter | F: 3× „Chci vědět víc“ → #vstupenky | Rozdělit CTA podle produktu a tagovat v Ecomailu (zájem: divadlo/koncerty/gastro/svatby/eventy) | S | 4 | P0 | Web dev + CRM |
| 9 | Svatební a eventová poptávka = stejný nekvalifikovaný formulář | F: identická pole, chybí rozpočet, typ akce, firma | Dva formuláře: svatba (termín, hosté, rozpočet od–do, ubytování), event (firma, typ, hosté, rozpočet, catering) + auto-odpověď do 1 min | M | 4 | P1 | Web dev + obchod |
| 10 | Žádné orientační ceny ani podmínky | F: ceny nikde; konkurence (Liblice, Loučeň, Ploskovice) je zveřejňuje | Zveřejnit „od“ ceny a co je v ceně pro svatby a pronájmy; u divadla cenové kategorie | S | 4 | P1 | Revenue manager |
| 11 | Předprodej 2027 nemá kanál | F: „Předprodej již brzy“, jen sběr e-mailů | Vybrat ticketing (GoOut/Enigoo), definovat sektory a ceny, early-bird pro databázi v prosinci 2026 | L | 5 | P1 | Revenue + web dev |
| 12 | Ecomail: 57 kontaktů, 0 kampaní, 1 list | F: ecomail_health | Welcome automatizace, měsíční „Deník obnovy“, tagy podle zájmu, double opt-in zachovat | S | 3 | P1 | CRM |
| 13 | 1,1 MB JS na one-pager | F: chunk 551 kB, celkem ~1,1 MB transfer | Při přestavbě: server components, bez zbytečných UI knihoven, next/image, WebP/AVIF; cíl < 300 kB JS | M | 3 | P1 | Web dev |
| 14 | Přístupnost: 14px písmo, kontrast 3,85:1, malé tap targety | F: lab měření | Základ 16px, zlatý text jen na tmavé, min. 44px cíle, audit WCAG AA po přestavbě | S | 3 | P1 | UX |
| 15 | Cookie lišta překrývá CTA a hero | F: screenshot; klik na „Poptat svatbu“ bez zavření banneru nejde | Lišta jako spodní pruh (ne modal), nepřekrývat obsah, zachovat Consent Mode v2 | S | 3 | P1 | Web dev |
| 16 | Nulová viditelnost v AI vyhledávání | F: proxy dotazy nezmiňují zámek, nebo citují prodej | Faktické stránky (historie, obnova, parametry prostor, FAQ), konzistentní entity (Organization/Place JSON-LD, Wikipedia, Wikidata), PR citace | M | 3 | P2 | SEO/GEO + PR |
| 17 | Žádný program/kalendář akcí | F: web bez jediné datované akce | /program s Event schema per akce, životní cyklus (před/po), i pro menší akce 2026/27 (advent, Dušičky) | M | 4 | P1 | Obsah + web dev |
| 18 | Chybí sociální důkaz | F: 0 referencí, 0 recenzí, FB/IG prázdné | Sbírat recenze z prvních akcí (GBP), citace z médií, partneři, „kdo za tím stojí“ | M | 3 | P2 | Marketing |
| 19 | 404 stránka výchozí anglická | F: „404: This page could not be found.“ | Vlastní 404 s navigací na program/svatby/kontakt | S | 1 | P2 | Web dev |
| 20 | Zdrojový kód webu mimo firemní repo (v0.app) | F: meta generator v0.app; repo nenalezeno | Převést projekt do GitHubu organizace, CI, preview deploy, přístupy pod firmou | S | 2 | P1 | Web dev |
