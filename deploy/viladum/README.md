# viladum.investimenti.cz – deploy kit

Statický web projektu **Viladům v zahradách** (byty Louny, Osvoboditelů 497) + brožura PDF.

## Stav (4. 10. 2026)

- DNS: `viladum.investimenti.cz` → wildcard `*.investimenti.cz` → Cloudflare tunnel → fortress. HTTPS funguje, bez Access.
- Dnes vrací 404 ze stránky „Neexistuje · INVESTIMENTI“ = catch-all kontejner `alias-redirects` (:8120). Chybí ingress pravidlo + obsah.
- Fortress konvence pro statické weby: `nginx:alpine` kontejner, ro bind z `/home/ubuntu/sites/<name>`, port `81xx` na `127.0.0.1`
  (`investimenti-root` :8110, `pilot-interiors-web` :8100, `alias-redirects` :8120). Tenhle web = **`viladum-web` :8130**.

## Obsah

| cesta | co to je |
|---|---|
| `site/index.html` | landing page (3 byty 3+kk, odkaz na brožuru, QR, kontakt) |
| `site/qr.png`, `site/qr.svg` | QR s `https://viladum.investimenti.cz/` |
| `qr-tisk-1200px.png` | QR pro tisk (stejná adresa) |
| `nginx/default.conf` | konfigurace nginx v kontejneru (`/brozura.pdf` jako attachment, Range, cache) |
| `deploy.sh` | nasazení z Macu: najde brožuru, nahraje, spustí kontejner, přidá ingress, ověří |
| `TASK-T-20261004-VILADUM-WEB.md` | pracovní blok pro Claude Code session na Macu |

Brožura **není v repu** (58 MB). Zdroj: Google Drive `Viladům v zahradách brožura.pdf`
(https://drive.google.com/file/d/1YXugxeR8_1Knl3h18dG_-_bFIcDH2t6p/view). Nikdy nepublikovat variantu `ROZPOČET …` (interní).

## Nasazení (Mac)

```bash
git clone --depth 1 -b ccr-0c2e43d7-ig8ual https://github.com/maroldova-sketch/investimenti-nexus /tmp/viladum-deploy
cd /tmp/viladum-deploy/deploy/viladum
BROZURA="$HOME/Downloads/Viladům v zahradách brožura.pdf" ./deploy.sh
```

`deploy.sh` je idempotentní. Předpoklad: na Macu funguje `ssh fortress` (uživatel `ubuntu`, sudo pro cloudflared).

## Ingress

- **Lokálně spravovaný tunel** (`/etc/cloudflared/config.yml` obsahuje `ingress:`): skript vloží
  `hostname: viladum.investimenti.cz → http://127.0.0.1:8130` před catch-all, zvaliduje a restartuje `cloudflared`.
- **Tunel spravovaný z dashboardu (token)**: skript to pozná a vypíše. Pravidlo pak přidej přes API
  (`PUT /accounts/{account}/cfd_tunnel/{tunnel}/configurations`, do `config.ingress` před položku bez `hostname`)
  nebo v Zero Trust → Networks → Tunnels → Public hostname. Token/ID tunelu jsou v `~/andrew_core` (viz
  `audits/DOMAIN_AUDIT_20260925.md`), nikdy je nevypisuj.
- Nouzová varianta bez zásahu do tunelu: přidat `server { server_name viladum.investimenti.cz; … }` do nginx
  v `alias-redirects` (`/home/ubuntu/sites/alias-redirects`) s mountem `/home/ubuntu/sites/viladum-web/html`.

## Kontrola po nasazení

1. `https://viladum.investimenti.cz/` → HTTP 200, stránka „Viladům v zahradách“.
2. `https://viladum.investimenti.cz/brozura.pdf` → `application/pdf`, stažení (Content-Disposition attachment).
3. QR (`site/qr.png`, `qr-tisk-1200px.png`) → `https://viladum.investimenti.cz/` — sken telefonem. Tisková brožura musí používat **tenhle** QR,
   aby tisk seděl s webem.
4. Kontaktní e-mail na webu je `j.caka@vzc.cz` – potvrdit nebo změnit v `site/index.html`.
