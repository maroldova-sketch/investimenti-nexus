# TOPOLOGY — „funguje odkudkoli" (cílový stav)

Cíl: veřejný přístup k MCP (mobil/chat) lepší než s mrtvým RPi — **VPS = veřejná
brána**, **Mac .43 = canonical backend** přes Tailscale.

> **Pozn. k běhu:** tento dokument vznikl v cloud sandboxu (ne na .43/VPS).
> Aktuální stav (`docs/TOPOLOGY-now.md`) i provedení změn vygenerují skripty
> v `tools/gateway/` spuštěné na nodech. Skripty jsou idempotentní a default
> dry-run; outward změny (DNS) jen s `--apply`.

## Architektura

```
  Mobil / claude.ai / chat
        │  (veřejný internet, z IP rozsahů Anthropicu)
        ▼
  Cloudflare  ──named tunnel──▶  VPS (cloudflared, STATELESS)
                                     │  reverse proxy
                                     ▼  Tailscale (MagicDNS)
                                 Mac .43 (canonical)
                                  ├─ Bible API   :8770
                                  ├─ Registry    :8110
                                  └─ NEXUS MCP    :8791
  HA: ponechat na hub.investimenti.cz / klod_mcp (jen ověřit).
```

### Hostnames (drž stávající, nové dle `*-mcp.investimenti.cz`)
| Hostname | → upstream (přes Tailscale) |
|----------|------------------------------|
| `bible-mcp.investimenti.cz` | `http://<MAC>:8770` (fallback: lokální RO replika) |
| `nexus-mcp.investimenti.cz` | `http://<MAC>:8791` (NEXUS MCP server) |
| `hub.investimenti.cz` | HA / klod_mcp (beze změny) |

## ZÁKON 9 — VPS stateless, žádné secrets

- **Secrets zůstávají na Macu** (trezor): `~/andrew/.env`, `~/andrew/secrets/secrets.json`,
  `~/andrew_core/.env`, `~/andrew_core/config/.env` (chmod 600, mimo git).
- **VPS nedrží klíče** — jen cloudflared **managed token** (v service) a proxy.
  Ingress se řídí přes CF dashboard/API (`INGRESS_MODE=managed`), ne config.yml
  se secrets na VPS.
- **CF API repoint DNS** se spouští **na Macu** (kde žije CF token), ne na VPS.
- VPS-side tajemství (pokud nutné) → **CF Workers Secrets**, ne soubor na VPS.

## Auth pro Claude.ai connector (ověřeno v docs, ne teorie)

Claude.ai custom connector (mobil/chat) **umí jen OAuth, nebo bez auth** — v UI
zadáš volitelně OAuth Client ID/Secret a projdeš OAuth flow. **Neposílá custom
hlavičky.** Důsledky:

| Metoda | Funguje pro mobilní connector? |
|--------|-------------------------------|
| Interaktivní SSO (CF Access) | ❌ MCP klient browser-SSO neprojde |
| **CF Access service token** (hlavičky `CF-Access-Client-Id/Secret`) | ❌ connector je neposílá |
| `X-API-Key` na bráně | ❌ connector ho neposílá |
| **OAuth 2.0 na MCP serveru** | ✅ nativní cesta connectoru |
| **Tajemství v URL** (neuhádnutelná cesta/query) | ✅ connector volá pevnou URL → secret se vždy přiloží |
| Bearer `authorization_token` | ✅ jen pro programové/Agent-SDK volání, ne UI |

**Doporučení:** brána pro mobil → buď MCP server s **OAuth**, nebo **secret-in-URL**
gateway (terminovaný na bráně). CF Access service token použij jen pro
server-to-server (Agent SDK), ne pro mobilní connector.

Zdroj: [Claude — custom connectors / remote MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp),
[MCP connector docs](https://docs.claude.com/en/docs/agents-and-tools/mcp-connector).

## Runbook (skripty v `tools/gateway/`, spouštěj na nodech)

| Krok | Skript | Node | Co dělá |
|------|--------|------|---------|
| T0 | `secrets_audit.sh` | Mac | kde leží klíče (JEN názvy), co chybí |
| T1 | `discover.sh` | VPS+Mac | CF DNS/tunely, Tailscale, docker, dosah na Mac → `TOPOLOGY-now.md` |
| T2/T4 | `setup_gateway.sh` | Mac (CF token) | tunnel + ingress + DNS repoint z RPi (dry-run; `--apply`) |
| T5 | `verify_external.sh` | mimo LAN/Tailnet | externí curl + Bible smoke |
| heal | `scripts/elias_mcp_heal.sh` | Mac/VPS | health + self-heal (už existuje) |

## Mac — neusínání + autostart (T5)
- `sudo pmset -c sleep 0 disksleep 0` (na napájení), nebo `caffeinate -dimsu` jako LaunchAgent.
- Tailscale autostart po rebootu (System Settings → Login, nebo `tailscale up` v LaunchDaemon).
- Ověř po rebootu: `tailscale status` + `cloudflared` service running.

## Mrtvý RPi (.220) — úklid
`discover.sh` najde DNS/ingress mířící na `192.168.1.220`; `setup_gateway.sh`
přepojí na tunel a (s `--apply`) smaže staré záznamy. Checkpoint: `dig` ukazuje
Cloudflare/tunel, ne `.220`.
