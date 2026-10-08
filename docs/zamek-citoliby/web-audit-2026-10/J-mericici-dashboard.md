# J. Měřicí dashboard

## J1. Datové zdroje (reálné)
| Zdroj | Co | Přístup | Stav dnes |
|---|---|---|---|
| GA4 property 557245267 | relace, kanály, události, key events, tržby (purchase) | GA4 Data API / Windsor (trial) | data od 7. 10. 2026 (5 relací) |
| GSC sc-domain:zamek-citoliby.cz | dotazy, imprese, kliky, pozice, CWV, indexace | GSC API / Windsor | 0 řádků (ověřit v UI) |
| GTM GTM-KQG9QF8H | definice událostí | GTM | obsah neauditován |
| Ecomail list 2 | kontakty, tagy, DOI, kampaně, CTR | Ecomail API (Elias Bridge ecomail_*) | 57 potvrzených, 0 kampaní |
| Meta (Pixel + stránky 1368510976347515, IG 17841426946147322) | dosah, leady, výdaje | Meta API / Windsor | 0 (nové účty / oprávnění) |
| Google Ads, Sklik | výdaje, konverze, CPA | API | účty neověřeny |
| Ticketing (po výběru) | objednávky, tržby, sektory, upsell | API/webhook/export | — |
| Interní CRM (citoliby.investimenti.cz) | leady, stav, hodnota, svatby, eventy | DB | existuje (dashboard repo), obsah neauditován |
| GBP | zobrazení, akce, recenze | GBP API / Windsor google_my_business | neověřeno |

## J2. KPI definice
| KPI | Definice | Zdroj | Frekvence | Typ dnes |
|---|---|---|---|---|
| Organická návštěvnost brand / nebrand | GSC kliky, dotaz obsahuje „cítoliby“/„resonance“ = brand | GSC | týdně | měřeno (0) |
| Pozice, imprese, CTR klíčových dotazů | 30 sledovaných dotazů z C2 | GSC | týdně | měřeno (0) |
| Indexované URL | GSC Pages „Indexed“ | GSC | týdně | neověřeno |
| Kvalifikované svatební poptávky | `generate_lead{lead_type:svatba}` **a** CRM stav „kvalifikováno“ (termín+hosté+rozpočet) | GA4 + CRM | týdně | neměřeno |
| Poptávky firemních akcí | `generate_lead{lead_type:event}` + CRM | GA4 + CRM | týdně | neměřeno |
| Konverzní poměr | leady / relace na landing page; purchase / relace /program | GA4 | týdně | — |
| Cena za kvalifikovaný lead (CPL) | výdaje kanálu / kvalifikované leady (CRM atribuce podle UTM + GCLID) | Ads + CRM | týdně | — |
| Tržby ze vstupenek | ticketing (zdroj pravdy), GA4 purchase pro atribuci | ticketing | denně v sezóně | — |
| Tržby z doplňkového prodeje | položky VIP/gastro/parkování/poukaz | ticketing | denně | — |
| Náklady na získání zákazníka (CAC) | (média + správa) / noví platící zákazníci | Ads + ticketing + CRM | měsíčně | — |
| ROMI | (tržby digitálně ovlivněné − marketing) / marketing | G model + skutečnost | měsíčně | cíl |
| Růst databáze | Ecomail potvrzené kontakty (DOI), podle tagu | Ecomail | týdně | měřeno (57) |
| Opakované nákupy / LTV | zákazníci s ≥ 2 nákupy / sezóna; tržba na e-mail | ticketing + CRM | měsíčně | — |
| GBP | zobrazení, kliky na web/trasa/volání, recenze a průměr | GBP | měsíčně | neověřeno |
| GEO viditelnost | 10 dotazů × 4 systémy: zmíněn / správně / doporučen | ruční | měsíčně | 0/10 |
| CWV | LCP/INP/CLS z GSC (field) | GSC | měsíčně | bez dat |

Rozlišení v dashboardu: **měřeno** (zdrojová data), **odhad** (model G), **cíl** (A/I). Každá karta nese štítek.

## J3. Měřicí plán událostí (GTM → GA4 → Meta)
Viz `impl/measurement-plan.md` (události, parametry, key events, deduplikace, consent).

## J4. Deduplikace a kontrola kvality
- Jedna konverze = jedno odeslání: událost se posílá až po úspěšné odpovědi server action (stav `success`), ne při kliknutí na submit; `event_id` = UUID z formuláře, stejné v GA4 (jako `transaction_id`/`lead_id`) a v Meta Pixel + CAPI.
- Ticketing: `purchase` jen z potvrzovací stránky/webhooku s `transaction_id`; GA4 dedupluje podle transaction_id; Meta Purchase s `event_id = transaction_id`.
- Testovací provoz: filtr interní IP + `debug_mode`; testovací e-maily s doménou firmy vyloučit z CRM metrik.
- Měsíční kontrola: GA4 purchase vs ticketing objednávky (odchylka ≤ 10 % — consent ztráta), leady GA4 vs CRM (odchylka ≤ 5 %).

## J5. Návrh rozložení (interní systém, 1 obrazovka)
1. Řádek: Tržby vstupenky (sezóna, denně) · Leady svatby/firemní (měsíc) · Databáze · ROMI (měsíc).
2. Řádek: Organika brand/nebrand (12 týdnů) · Top dotazy a pozice · Indexace.
3. Řádek: Kanály → leady/tržby/CPA (tabulka) · Obsazenost per představení (heatmapa) · Upsell podíl.
4. Řádek: GBP · GEO skóre · CWV · Kvalita dat (odchylky J4).
