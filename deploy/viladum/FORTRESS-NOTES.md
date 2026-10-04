# Fortress – co už víme (4. 10. 2026, zjištěno přes Elias Bridge, read-only)

Doplněk k `CLAUDE.md` / `TASK-T-20261004-VILADUM-WEB.md`. Nic z toho nenahrazuje kontrolu přes SSH; šetří to jen čas.

- `https://viladum.investimenti.cz/` dnes vrací **404 ze stránky „Neexistuje · INVESTIMENTI“** – to je catch-all kontejner
  **`alias-redirects`** (nginx, `127.0.0.1:8120`, `/home/ubuntu/sites/alias-redirects`), který v registru obsluhuje
  `*.investimenti.cz` + `liveboard/lopat/owui`. Tunel tedy už `viladum.*` na fortress směruje; chybí jen vhost + obsah.
- Statické weby na fortressu jsou **samostatné `nginx:alpine` kontejnery s ro bind mountem**, každý na vlastním portu:
  `investimenti-root` → `:8110`, `/home/ubuntu/sites/investimenti-root` (apex, za Access, **neměnit**);
  `pilot-interiors-web` → `:8100`, `/home/ubuntu/pilot/interiors-web`; `alias-redirects` → `:8120`.
  Origin je HTTP za Cloudflare tunnelem (`cloudflared`, `/etc/cloudflared`), TLS termínuje Cloudflare.
- Dvě schůdné cesty (vyber podle `docker inspect` + nginx výpisu, ne podle názvu):
  1. **Vhost v `alias-redirects`** (žádný zásah do tunelu): `deploy.sh --mode container --container alias-redirects`,
     `--nginx-conf <host mount conf.d>/viladum.conf`, `--root <host mount>/viladum`, `--nginx-root <container mount>/viladum`,
     `--listen 80`. Funguje jen pokud nginx v tom kontejneru includuje adresář s konfigy a má mount, kam jde dát `viladum/`.
  2. **Nový kontejner `viladum-web` na `127.0.0.1:8130`** (`/home/ubuntu/sites/viladum-web`) + ingress pravidlo
     `viladum.investimenti.cz → http://127.0.0.1:8130` v Cloudflare tunelu **před** catch-all. Pokud je tunel spravovaný
     z dashboardu (token), pravidlo se přidává přes Cloudflare API/dashboard; údaje jsou v `~/andrew_core`
     (`audits/DOMAIN_AUDIT_20260925.md`), tokeny nevypisovat.
- Disk fortress: 95 % plný, ~10 GB volných. Balíček `public/` má 28 MB – stačí, ale nekopírovat zbytečně víckrát.
- Port `8130` je v registru volný; před použitím ověř `ss -ltn`.
