# NEXUS MCP server

Vystavuje NEXUS jako MCP nástroje, aby ho Elias (a jakákoli Claude relace / mobil)
mohl ovládat. Server je **tenký obal** nad strojovým JSON API (`/api/v1/*`) —
veškerá logika i autorizace (scopes) zůstává v Nexusu.

```
Claude relace / mobil  ──MCP──▶  nexus_mcp.py  ──HTTP+API-key──▶  NEXUS /api/v1/*
```

## 1. Vytvoř API-key (na nodu s Nexusem)

```bash
python scripts/nexus_token.py create "elias-mcp" \
    --scopes fleet:read,people:read,fortis:read,notify:read,notify:write,mail:send,idoklad:read,idoklad:write,imports:run
# nebo plný přístup:
python scripts/nexus_token.py create "elias-admin" --scopes admin
```

Plný token (`nxs_...`) se ukáže **jen jednou** — ulož ho jako `NEXUS_API_KEY`.

## 2. Nainstaluj závislosti

```bash
pip install -r mcp/requirements.txt
```

## 3a. Lokální stdio (Claude Desktop / Elias na stejném nodu)

```bash
NEXUS_API_BASE=http://127.0.0.1:8000 NEXUS_API_KEY=nxs_... python mcp/nexus_mcp.py
```

Registrace v Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nexus": {
      "command": "python",
      "args": ["/cesta/k/investimenti-nexus/mcp/nexus_mcp.py"],
      "env": {
        "NEXUS_API_BASE": "http://127.0.0.1:8000",
        "NEXUS_API_KEY": "nxs_..."
      }
    }
  }
}
```

## 3b. Remote HTTP (mobil / claude.ai — přes cloudflared tunel)

```bash
NEXUS_MCP_HTTP=1 NEXUS_MCP_PORT=8791 NEXUS_API_KEY=nxs_... python mcp/nexus_mcp.py
```

Pak vystav přes cloudflared (stejně jako `bible-mcp`), např.
`nexus-mcp.investimenti.cz → http://127.0.0.1:8791`, a přidej jako
**custom connector** v Claude (Settings → Connectors). Tím to máš dostupné
i z mobilu a jiných relací.

> Doporučení: `bible-mcp` už takhle běží — přidej `nexus-mcp` do stejného
> cloudflared configu a do `elias_mcp_heal.sh` ENDPOINTS, ať to self-heal hlídá.

## Dostupné nástroje

| Nástroj | Scope | Co dělá |
|---------|-------|---------|
| `nexus_ping` | (jakýkoli) | identita + scopes klíče |
| `atlas_kpis` | fortis:read | KPI holdingu |
| `fleet_vehicles` | fleet:read | seznam vozidel |
| `people` | people:read | seznam osob |
| `fortis_documents` | fortis:read | ekonomické doklady |
| `notifications` | notify:read | čtení notifikací |
| `create_notification` | notify:write | vytvoření notifikace |
| `send_mail` | mail:send | odeslání e-mailu (M365) |
| `run_import` | imports:run | spuštění importu (fleet/fuel) |
| `idoklad_invoices` | idoklad:read | faktury z iDokladu |
| `idoklad_sync` | idoklad:write | sync iDoklad → Fortis |

Scopes vynucuje Nexus, ne MCP server — i kdyby klíč „uměl" víc nástrojů,
bez scope dostane 403.
