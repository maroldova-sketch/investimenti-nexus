# zamek-citoliby.cz

Veřejný web zámku Cítoliby. Statický, bez build kroku, určený pro **Cloudflare Pages** (doména už je v Cloudflare).
Interní liveboard citoliby.investimenti.cz se tohoto webu netýká.

## Nasazení (10 minut)

1. Cloudflare → Workers & Pages → **Create → Pages → Connect to Git** → repo `maroldova-sketch/investimenti-nexus`, větev `main`.
2. Build settings: Framework **None**, Build command prázdný, **Root directory** `frontend/zamek-citoliby`, Output directory `/` (tečka).
3. Deploy. Ověřit na `*.pages.dev` adrese.
4. Custom domains → přidat `zamek-citoliby.cz` a `www.zamek-citoliby.cz`. Cloudflare sám přepíše DNS záznam, který dnes vrací 522 (starý origin). Nic jiného v DNS neměnit (MX pro M365 zůstává).
5. Settings → Environment variables (Production):
   - `ECOMAIL_API_KEY`, `ECOMAIL_LIST_ID` — newsletter (Ecomail → Nastavení → API; seznam „Předprodej 2027“ s double opt-in).
   - `RESEND_API_KEY`, `NOTIFY_EMAIL` (kam chodí svatební poptávky), `FROM_EMAIL` (ověřená doména v Resend, např. `Zámek Cítoliby <web@zamek-citoliby.cz>`).
   - `WEBHOOK_URL` volitelně (Make / n8n / Google Sheet), dostane každý zápis i poptávku jako JSON.
   Bez proměnných formuláře vrací srozumitelnou chybu, web funguje.
6. `assets/config.js`: doplnit `metaPixelId`, `ga4Id` až se spouští reklama, a `ticketsUrl` 24. 11. 2026 (tím se na webu objeví tlačítka Vstupenky).

## Obsah

- `data/program.json` — jediný zdroj programu. Pole `public` (zobrazit), `announced` (rozsvítí okno na fasádě), `status` (`plán` / `potvrzeno`), `tickets` (deep link na prodejce k dané akci). Do budoucna generovat z Castello Hubu.
- Fotky: všechny bloky `class="ph"` jsou placeholdery s popisem, co tam patří. Nahradit `<img>` po říjnovém fotoshootu (šířka 1600 px, WebP).
- Texty bez cen a bez jmen umělců, dokud nejsou podepsané smlouvy. Ceny doplní Honza, tituly Kristýna.
- Telefon zatím není, kontakt je jen e-mail.

## Struktura

index · program · resonance · koncerty · gastro · svatby (poptávka) · pribeh · navsteva · kontakt · soukromi
`functions/api/subscribe.js`, `functions/api/poptavka.js` = Pages Functions (server), `_headers`, `robots.txt`, `sitemap.xml`.

## Měření

Meta Pixel a GA4 se načítají až po souhlasu v cookie liště. Klik na „Vstupenky“ posílá `InitiateCheckout` / `begin_checkout`. Všechny odkazy z reklam vést na web s UTM, nikdy přímo na prodejce.
