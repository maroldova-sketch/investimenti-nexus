# H. Implementační backlog

Strojově čitelná verze: `backlog.yaml` (import do citoliby.investimenti.cz / MAXINA). ID stabilní, stav se aktualizuje v systému, ne zde.

Formát: **ID · Název · Role · Priorita · Náročnost** — Úkol → Akceptační kritéria → Ověřovací test.

## P0 — do 7 dnů (stávající web, bez přestavby)

**WEB-001 · robots.txt a sitemap.xml · dev · P0 · S**
Přidat `app/robots.ts` a `app/sitemap.ts` (impl/). → `GET /robots.txt` 200 s `Sitemap:` řádkem; `GET /sitemap.xml` 200, validní XML, obsahuje `/`. → `curl -I`, GSC → Sitemaps → „Úspěch“.

**WEB-002 · Canonical + metadataBase · dev · P0 · S**
`metadata.metadataBase = new URL('https://www.zamek-citoliby.cz')`, `alternates.canonical: '/'`. → HTML obsahuje `<link rel="canonical" href="https://www.zamek-citoliby.cz/">`. → grep v HTML.

**WEB-003 · Title/description/H1 homepage · SEO+dev · P0 · S**
Nasadit texty z E1. → title ≤ 60 znaků s „divadlo, svatby, gastronomie u Loun“; H1 obsahuje „Zámek Cítoliby“ + produkt. → Rich Results / Lighthouse SEO.

**WEB-004 · JSON-LD Organization + Place · dev · P0 · S**
Vložit `impl/jsonld-organization.json` (doplnit telefon, adresu, IČO, sameAs). → Schema validator bez chyb; GSC bez varování. → validator.schema.org.

**WEB-005 · Kontaktní blok a patička s NAP · dev+obchod · P0 · S**
Telefon (tel:), adresa, mapa (odkaz, embed až po souhlasu), IČO, sídlo, odpovědní doba. → Všechny údaje shodné s GBP a `marketing/NAP.md`. → vizuální kontrola + JSON-LD shoda.

**WEB-006 · Skutečné fotografie místo ilustrace · marketing · P0 · M**
Focení (exteriér, nádvoří, arkády, sál, zahrada, obnova, tým) ≥ 40 snímků, výběr 20 na web; hero + sekce „Fotografie“ = galerie. OG image 1200×630 fotografie < 200 kB. → hero `<img>` je fotografie s popisným alt; galerie ≥ 12 fotek; LCP obrázek preloaded. → Lighthouse, vizuálně.

**WEB-007 · Měření konverzí v GTM/GA4 · analytik · P0 · M**
Implementovat `impl/measurement-plan.md`: dataLayer push při úspěšném odeslání (server action → stav success → `generate_lead`/`newsletter_signup`), `cta_click`, `contact_click`, `outbound_click`; GA4 key events; Meta standardní události s `event_id`. → V GA4 DebugView vidět události s parametry; Meta Events Manager vidí Lead s deduplikací. → test odeslání formulářů (testovací e-mail s +tag), kontrola, že 1 odeslání = 1 konverze.

**WEB-008 · CTA podle produktu + tag zájmu v Ecomailu · dev+CRM · P0 · S**
„Chci vědět víc“ u Divadlo/Hudba/Gastro → formulář s předvyplněným `source` (divadlo/koncerty/gastro); Ecomail tag `zajem:*`. → Kontakt v Ecomailu má tag podle zdroje; DOI zachováno. → testovací přihlášení ×3.

**LOC-001 · Google Business Profile · lokální SEO · P0 · S**
Nárokovat/založit, kategorie, NAP, fotografie 20+, popis, odkazy (web, vstupenky). → Profil ověřen, všechna pole vyplněna, bez fiktivní otevírací doby. → screenshot + kontrola v Mapách.

**LOC-002 · Firmy.cz, Mapy.cz, Kudyznudy, Dolní Poohří · lokální SEO · P0 · S**
Založit/aktualizovat profily s NAP a odkazem. → 4 profily živé, shodné NAP. → odkazy v `NAP.md`.

**PR-001 · Oprava zastaralých informací · PR · P0 · M**
hrady.cz (správce profilu), Wikipedia „Cítoliby (zámek)“ (neutrálně, s citacemi), turistika.cz, kultura.cz; tisková zpráva „Zámek ožívá“. → Wikipedia odstavec „Současnost“ s citací na tisk; hrady.cz bez „nepřístupný/na prodej“; ≥ 2 mediální výstupy. → odkazy.

**UX-001 · Cookie lišta nepřekrývá obsah · dev · P0 · S**
Lišta jako spodní pruh bez overlay; CTA klikatelné bez interakce s lištou; Consent Mode v2 beze změny. → Playwright: klik na „Poptat svatbu“ bez zavření lišty otevře dialog. → test v `data/` skriptu.

## P1 — do 30 dnů

**WEB-010 · Repo pod firmou + CI + preview · dev · P1 · S**
Přesun v0.app projektu do GitHub organizace, Vercel projekt pod firemním účtem, branch preview, `.env` správa. → `git clone` funguje, deploy z main, preview na PR. → PR test.

**WEB-011 · Vícestránková architektura fáze 1 · dev · P1 · L**
Stránky: /program, /program/[slug], /divadlo, /svatby, /firemni-akce, /historie, /obnova-zamku, /navsteva, /fotografie, /pamet-mista, /kontakt, /ochrana-osobnich-udaju; CMS (doporučení: Sanity nebo Payload; alternativa MDX v repu pro start) s typy Event, Space, Post, Page. Navigace + patička + breadcrumbs. → Každá stránka: unikátní title/description/H1/canonical/BreadcrumbList; Lighthouse SEO ≥ 95, Performance ≥ 85 mobil; JS ≤ 300 kB. → Lighthouse CI + Playwright smoke (všechny URL 200, žádný 404 v navigaci).

**WEB-012 · Formuláře svatba / event oddělené, vícekrokové · dev · P1 · M**
Pole dle E2/E3; honeypot zachovat; rate limit; uložení do interního CRM + e-mail notifikace + auto-odpověď; `generate_lead` s `lead_type`, `budget_band`, `guests`. → Lead v CRM do 10 s, auto-odpověď do 1 min, GA4 událost 1×. → e2e test.

**WEB-013 · Event stránky s JSON-LD a životním cyklem · dev · P1 · M**
Šablona dle D4/E5; `impl/jsonld-event-example.json`; po akci skryt Offer, zachována URL. → Rich Results Test: Event validní; po datu konání stránka 200 bez Offer. → test na 1 akci.

**WEB-014 · Výkon a přístupnost · dev · P1 · M**
Bundle analýza, odstranit nepoužité UI knihovny, `next/image` AVIF/WebP, 16px base, kontrast ≥ 4,5:1 (zlatá jen na tmavé), tap targets ≥ 44px, focus stavy. → Lighthouse a11y ≥ 95; axe 0 critical. → axe + Lighthouse CI.

**WEB-015 · Vlastní 404 + přesměrování · dev · P1 · S**
Česká 404 s odkazy; 301 mapa pro případné změny URL. → `/neexistuje` 404 česky; staré kotvy fungují na homepage. → curl.

**TIX-001 · Výběr ticketingu · revenue+dev · P1 · M**
Kritéria: plán sálu (900 + 60 VIP), sektory, upsell položky, dárkové poukazy, provize, export dat (API/webhook), GA4/Meta měření s transaction_id, iframe/redirect UX, podpora Seznam/Google Event „Vstupenky“. Kandidáti: GoOut, Enigoo, Colosseum, SmsTicket, Ticketportal. → Rozhodnutí + smlouva; testovací událost prodaná end-to-end s purchase událostí v GA4. → testovací nákup.

**CRM-001 · Welcome série + segmentace · CRM · P1 · S**
3 e-maily, tagy zájmu, early-bird segment. → Nový kontakt dostane D0/D3/D10; tag podle zdroje. → testovací kontakt.

**CRM-002 · Svatební a firemní follow-up automatizace · CRM+obchod · P1 · M**
Dle F6; úkoly v interním systému (telefonát D1, nabídka 48 h). → Každý lead má úkol s termínem; e-maily D3/D10. → test.

**ADS-001 · Google Ads + Sklik + Meta účty, konverze, brand kampaň · PPC · P1 · S**
Založit/ověřit účty pod firmou, propojit GA4 konverze, Consent Mode, brand kampaň on. → konverze importovány, brand kampaň aktivní s CTR > 20 %. → účty screenshot.

**ADS-002 · Svatební kampaň Search (Google + Sklik) · PPC · P1 · M**
Spustit po WEB-011 (/svatby). → CPL ≤ 1 200 Kč po 30 dnech nebo pauza a revize. → týdenní report.

**SEO-001 · Seznam Webmaster + GSC sitemap + monitoring · SEO · P1 · S**
→ Obě property s odeslanou sitemapou; týdenní export do dashboardu. → J.

**CNT-001 · Obsah fáze 1 · redakce · P1 · L**
Texty E1–E6 finalizovat (ceny od revenue managera), /historie kap. 1–2, /obnova-zamku timeline + 3 kapitoly, FAQ svatby/firemní. → Všechny stránky fáze 1 bez placeholderů `[ ]`. → redakční kontrola.

## P2 — do 90 dnů

**WEB-020 · Fáze 2 stránek** (/koncerty, /svatby/prostory, /svatby/cenik-a-podminky, /pronajem-prostor, /prostory/[slug], /gastronomie, /slavnosti, /novinky, /o-nas, /obchodni-podminky-vstupenky) · dev+obsah · P2 · L → kritéria jako WEB-011.

**WEB-021 · Technické listy prostor (PDF) + stažení za e-mail (volitelné)** · marketing · P2 · M → `file_download` událost, Ecomail tag `zajem:eventy`.

**WEB-022 · Kalendář volných svatebních termínů 2027** · dev · P2 · S → zdroj = interní systém; obsazené termíny automaticky.

**WEB-023 · Dárkové poukazy** (ticketing nebo vlastní) · revenue+dev · P2 · M → nákup měřen jako purchase s item `voucher`.

**WEB-024 · Meta Conversions API** · analytik · P2 · M → deduplikace ověřena v Events Manageru (event_id shoda ≥ 90 %).

**WEB-025 · CSP hlavička** · dev · P2 · S → GTM/GA4/Meta/Ecomail/ticketing whitelist; 0 console CSP chyb.

**SEO-002 · Svatební a eventové katalogy** (10 registrací) · lokální SEO · P2 · S.

**SEO-003 · GEO monitoring** (10 dotazů/měsíc) · SEO · P2 · S.

**CNT-002 · 90denní kalendář obsahu (F4) splněn** · redakce · P2 · L.

**ADS-003 · Předprodej 2027 kampaně (per-event, PMax, Meta)** · PPC · P2 · L → ROAS ≥ 3 po 4 týdnech.

**DATA-001 · Dashboard (J) v interním systému** · analytik+dev · P2 · M → denní import GA4/GSC/Ecomail/ticketing/CRM, definice KPI.

**EN-001 · EN verze /svatby, /firemni-akce, /program (hreflang)** · dev+obsah · P2 (H2 2027) · M.
