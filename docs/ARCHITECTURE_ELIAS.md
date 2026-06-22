# Elias × NEXUS — řídicí architektura (master)

Cíl: **Elias ovládá z mobilu i jakékoli relace úplně všechno** — Nexus, Fortis,
iDoklad, maily (M365), workflow (n8n), HA, „bibli" a setup. Tenhle dokument
mapuje stav, co je hotové v tomhle repu, a co ještě chybí napříč systémy.

## Topologie

```
┌─ Claude relace / MOBIL / claude.ai ─┐
│            (Elias)                  │
└───────────────┬─────────────────────┘
                │  MCP (HTTP/SSE přes cloudflared, nebo stdio lokálně)
   ┌────────────┼───────────────┬───────────────┬──────────────┐
   ▼            ▼               ▼               ▼              ▼
bible-mcp   nexus-mcp        n8n-mcp        ha-klod-mcp     (další)
(veřejné)   (NOVÉ ↓)         (cloud)        (cloud)
            │
            ▼  HTTP + API-key (X-API-Key: nxs_...)
        NEXUS /api/v1/*  ──▶  SQLite, M365 Graph, iDoklad, importy
```

Self-heal: `scripts/elias_mcp_heal.sh` (systemd/launchd timer) hlídá všechny
endpointy, lokální restartuje, výpadky píše do Telegramu i Nexus notifikací.

## Co je HOTOVÉ v tomhle repu (PR)

| Komponenta | Soubor | Stav |
|------------|--------|------|
| Strojová auth (API-key + scopes) | `backend/core/security/service_auth.py`, `backend/modules/mcp_api/models.py` | ✅ |
| Správa tokenů (CLI) | `scripts/nexus_token.py` | ✅ |
| Strojové JSON API `/api/v1/*` | `backend/modules/mcp_api/routes.py` | ✅ |
| Webhook HMAC podpis | `service_auth.verify_webhook_signature` + `webhooks/routes.py` | ✅ |
| iDoklad klient + sync do Fortis | `backend/integrations/idoklad/`, `backend/modules/idoklad/routes.py` | ✅ |
| Nexus MCP server | `mcp/nexus_mcp.py`, `mcp/README.md` | ✅ |
| Self-heal: registry + Nexus notify | `scripts/elias_mcp_heal.sh` | ✅ |

**Scopes:** `fleet:read people:read fortis:read notify:read notify:write
mail:send idoklad:read idoklad:write imports:run admin`.

## Zprovoznění (na nodu s Nexusem)

```bash
# 1) vytvoř token pro Elias
python scripts/nexus_token.py create "elias-mcp" --scopes admin
# 2) nastav .env (viz .env.example): WEBHOOK_SECRET, IDOKLAD_*, M365_*
# 3) spusť MCP server (lokálně stdio, nebo HTTP za cloudflared)
NEXUS_API_KEY=nxs_... python mcp/nexus_mcp.py            # stdio
NEXUS_MCP_HTTP=1 NEXUS_API_KEY=nxs_... python mcp/nexus_mcp.py   # remote
# 4) vystav nexus-mcp přes cloudflared (jako bible-mcp) → custom connector v Claude
# 5) přidej nexus-mcp do registry.json, ať to heal hlídá
```

## Co ještě CHYBÍ (mimo tenhle repo)

Pořadí dle páky:

1. **cloudflared tunel pro `nexus-mcp`** (a registru/dave-bridge) — bez něj to
   z mobilu nedosáhneš. `bible-mcp` už takhle běží, jen replikovat config.
2. **Registry jako jediný zdroj pravdy** — naplnit `~/elias/registry.json`
   katalogem všech služeb (name/url/type/scopes). Heal už ho čte.
3. **n8n workflows** — verzovat exporty workflow do repa, vystavit trigger
   nástroje přes `n8n-mcp`, zdokumentovat inventář.
4. **iDoklad write** (vystavení/úhrada faktur) — klient má jen čtení + sync;
   `create_issued_invoice` / `mark_paid` doplnit dle reálných polí v3 API.
5. **M365 víc schránek** — dnes jedna sdílená přes refresh token. Pro per-entity
   maily přejít na app-only Graph (client_credentials) + Mail.Send aplikační.
6. **Centralizace secrets** — místo více `.env` na nodech jeden zdroj (1Password/
   sops/Vault) + rotace; registry odkazuje, kde co je.
7. **Cross-system audit** — `notify_nexus` je první krok; cílově každá akce
   Elias→systém padá do `audit_log` (mail odeslán, faktura, workflow spuštěn).
8. **MCP tool-level health** — heal teď testuje HTTP; přidat ověření, že MCP
   server reálně listuje nástroje (ne jen že odpovídá 200).

## Bezpečnostní poznámky

- Tokeny: v DB jen hash (pbkdf2), plný `nxs_...` se ukáže jen při vytvoření.
- Scopes vynucuje Nexus, ne MCP server → kompromitovaný MCP klíč nepřekročí scope.
- Webhooky: nastav `WEBHOOK_SECRET` → vynutí HMAC podpis (jinak jsou otevřené!).
- `admin` scope dávej jen tokenu, kterému opravdu věříš (Elias core).
