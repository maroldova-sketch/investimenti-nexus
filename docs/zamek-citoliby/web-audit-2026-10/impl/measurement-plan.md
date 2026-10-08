# Měřicí plán — GTM `GTM-KQG9QF8H` → GA4 `G-J6VFT3CS1C` → Meta Pixel (+ CAPI)

Consent: stávající ConsentProvider + Consent Mode v2 zachovat; tagy GA4/Meta spouštět jen při `analytics_storage`/`ad_storage` granted (dnes funguje). Všechny události pushovat do `dataLayer` bez ohledu na souhlas (GTM je filtruje).

| Událost (dataLayer) | Kdy | Parametry | GA4 key event | Meta |
|---|---|---|---|---|
| `generate_lead` | po úspěšné server action poptávky (stav success) | `lead_type` (svatba\|event), `lead_id` (UUID), `guests`, `budget_band`, `preferred_month`, `page_path` | ✅ (hodnota: svatba 2 000, event 1 500 — interní ohodnocení) | `Lead` s `event_id = lead_id` |
| `newsletter_signup` | po úspěšném odeslání (před DOI) | `source` (novinky\|vstupenky\|divadlo\|koncerty\|gastro\|svatby\|eventy), `signup_id` | ✅ (hodnota 50) | `Subscribe` s `event_id` |
| `newsletter_confirm` | Ecomail webhook → server → GA4 Measurement Protocol (volitelné) | `source` | — | — |
| `photo_story_submit` | po úspěšném uploadu | `kind` | — | — |
| `cta_click` | klik na primární CTA | `cta_id`, `cta_text`, `target` | — | — |
| `contact_click` | tel:/mailto:/mapa | `method` (phone\|email\|map) | ✅ (phone) | `Contact` |
| `begin_checkout` | klik „Koupit vstupenky“ (odchod do ticketingu) | `event_slug`, `event_date` | — | `InitiateCheckout` |
| `purchase` | potvrzovací stránka/iframe postMessage/webhook z ticketingu | `transaction_id`, `value`, `currency`, `items[]` (event_slug, sector, qty, price, item_category: ticket\|vip\|gastro\|parking\|voucher) | ✅ (ecommerce) | `Purchase` s `event_id = transaction_id` |
| `file_download` | technický list, svatební brožura | `file_name` | — | — |
| `view_event` | zobrazení detailu akce | `event_slug`, `days_to_event` | — | `ViewContent` |
| `outbound_click` | odkazy na ticketing/partnery | `link_url` | — | — |

Pravidla:
1. Událost konverze až po odpovědi serveru (ne na submit) — 1 odeslání = 1 událost; UUID pro deduplikaci GA4 (jako `transaction_id` u leadů) a Meta `event_id`.
2. UTM + `gclid`/`fbclid` uložit do skrytých polí formuláře → CRM (atribuce leadu).
3. GA4: vyloučit interní provoz (IP filtr), `debug_mode` na preview doméně, cross-domain měření s doménou ticketingu (pokud redirect).
4. Meta CAPI (fáze 2): server-side odeslání `Lead`/`Purchase` se stejným `event_id`; cíl deduplikace ≥ 90 % v Events Manageru.
5. Měsíční smoke test: Playwright odešle testovací formulář → kontrola v GA4 DebugView + Ecomail (testovací kontakt smazat).
