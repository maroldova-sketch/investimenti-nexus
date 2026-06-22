# T1 — Mapa dosahu (REACH)

> **Kontext běhu (ověřeno, ne předpoklad):** tato relace běžela v **cloudovém
> sandboxu** (`hostname=vm`, `/root`, Linux), **ne na Macu .43**. Proto živé
> proby lokálních/LAN/SSH služeb a systémů vyžadujících `~/andrew/.env` **odsud
> nešly** — není to chybějící klíč, ale jiné prostředí. Autoritativní mapu
> vygeneruje `scripts/reach_probe.sh` spuštěný **na .43**.

Datum auditu: 2026-06-22.

## A) Ověřeno z této relace

| Systém | Endpoint | Stav | Důvod |
|--------|----------|------|-------|
| NEXUS (kód) | `import main` + `app.routes` | **OK** | App nabíhá, **140 rout**, 11 MCP nástrojů (viz CAPABILITIES.md) — ověřeno z běžící app, ne z paměti |
| M365 Graph (síť) | `graph.microsoft.com` | **OK (jen TCP)** | HTTP 200 na síťové vrstvě; **token test nešel** — žádné `M365_*` creds v sandboxu |
| bible-api | `localhost:8770/health` | **FAIL** | HTTP 000 — služba zde neběží (běží na .43) |
| registry | `192.168.1.43:8110/health` | **FAIL** | HTTP 000, LAN timeout 5 s — síť .43 odsud nedostupná |
| fortress | `ssh://fortress` | **FAIL** | `ssh` ani `tailscale` binárka v sandboxu není |
| Home Assistant | `/api/` | **FAIL** | `HA_URL`/`HA_TOKEN` nejsou (žádné `~/andrew/.env`) |
| n8n | `/healthz`, `/rest/active` | **FAIL** | `N8N_URL` není |
| Cloudflare | `tokens/verify` | **FAIL** | `CLOUDFLARE_API_TOKEN` není |

## B) PENDING — spustit na .43

Autoritativní T1 mapa = jeden příkaz na nodu .43:

```bash
cd <nexus-repo> && ./scripts/reach_probe.sh
# přepíše docs/REACH.md skutečnými OK/FAIL ze všech 8 systémů
```

`reach_probe.sh` ověří (jen čtení, žádné zápisy do cizích systémů):

| Systém | Co testuje |
|--------|-----------|
| bible-api | `GET localhost:8770/health` + smoke `POST /sessions` |
| registry | `GET 192.168.1.43:8110/health` |
| NEXUS | `GET 127.0.0.1:8000/health` + detekce běhu (launchd/docker) + repo (`rg`) |
| fortress | `ssh` přes Tailscale → `uname -a`, `docker ps` |
| M365 | client_credentials token z `~/andrew/.env` → `GET /users/{M365_MAILBOX}` (read-only) |
| Home Assistant | `GET {HA_URL}/api/` s `HA_TOKEN` |
| n8n | `GET {N8N_URL}/healthz` + `rest/active-workflows` |
| Cloudflare | `GET tokens/verify` (whoami) |

Skript čte konfiguraci z `~/andrew/.env` (přepsatelné: `ANDREW_ENV`, `NEXUS_PORT`,
`FORTRESS_HOST`, `HA_URL/HA_TOKEN`, `N8N_URL/N8N_API_KEY`, `CLOUDFLARE_API_TOKEN`).

> **Checkpoint T1:** tabulka výše. 1× OK (NEXUS kód), 1× OK-TCP (Graph), zbytek
> PENDING na .43. Spuštění `reach_probe.sh` na .43 doplní reálné OK/FAIL.
