# TASK T-20261004-VILADUM-WEB — nasadit viladum.investimenti.cz na fortress

Pro Claude Code session na Macu (má `ssh fortress`). Jeden report na konci. Nic jiného na fortressu neměnit.

## Kontext
- DNS + HTTPS hotové (wildcard `*.investimenti.cz` → tunnel → fortress). Web vrací 404 z catch-all `alias-redirects` (:8120).
- Deploy kit: repo `maroldova-sketch/investimenti-nexus`, větev `ccr-0c2e43d7-ig8ual`, složka `deploy/viladum/`.
- Brožura (58 MB) není v repu. Zdroj Google Drive: `Viladům v zahradách brožura.pdf` (ID `1YXugxeR8_1Knl3h18dG_-_bFIcDH2t6p`).
  **Ne** variantu `ROZPOČET …` (interní).

## Kroky
1. **Stáhnout kit** (ne do kanonických adresářů):
   `git clone --depth 1 -b ccr-0c2e43d7-ig8ual https://github.com/maroldova-sketch/investimenti-nexus /tmp/viladum-deploy`
   Kontrola: `ls /tmp/viladum-deploy/deploy/viladum/site/index.html`
2. **Najít brožuru na Macu**: `mdfind -name "Viladům v zahradách brožura" | grep -vi rozpo`, případně
   `~/Library/CloudStorage/GoogleDrive-*/` nebo `~/Downloads`. Když není lokálně, stáhnout z Drive
   (Drive for Desktop / `gdown 1YXugxeR8_1Knl3h18dG_-_bFIcDH2t6p` / prohlížeč). Kontrola: `file` říká PDF, velikost ≈ 58 MB.
3. **Dry-run**: `cd /tmp/viladum-deploy/deploy/viladum && BROZURA="<cesta>" ./deploy.sh --dry-run`
   Kontrola: skript vidí SSH na fortress a brožuru.
4. **Nasadit**: `BROZURA="<cesta>" ./deploy.sh`
   Kontrola: `docker ps | grep viladum-web`, `curl -H 'Host: viladum.investimenti.cz' http://127.0.0.1:8130/` na fortressu vrací 200.
5. **Ingress**: pokud skript vypíše `INGRESS: lokální config … nenalezen`, je tunel spravovaný z Cloudflare.
   Přidat public hostname `viladum.investimenti.cz → http://127.0.0.1:8130` před catch-all `*.investimenti.cz`
   (API `cfd_tunnel/{id}/configurations` nebo dashboard). Údaje k tunelu jsou v `~/andrew_core/audits/DOMAIN_AUDIT_20260925.md`;
   tokeny nevypisovat. Záloha stávající konfigurace před změnou.
   Kontrola: `curl -sI https://viladum.investimenti.cz/ | head -1` → `200`.
6. **Ověřit zvenku**:
   - `https://viladum.investimenti.cz/` → 200 + stránka „Viladům v zahradách“
   - `https://viladum.investimenti.cz/brozura.pdf` → `application/pdf`, stažení
   - `https://viladum.investimenti.cz/qr.png` → QR vede na `https://viladum.investimenti.cz/`

## Report (jeden, na konci)
- co je nasazeno (kontejner, port, cesta na fortressu, velikost brožury web/tisk)
- jak byl vyřešen ingress (lokální config / API / dashboard / nouzová varianta)
- výsledky 3 kontrol zvenku (HTTP kódy)
- co zbývá pro Honzu (např. potvrdit kontaktní e-mail `j.caka@vzc.cz` na webu)
