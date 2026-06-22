# elias_mcp_heal.sh

Node-agnostic health-check a self-heal pro Elias MCP / bridge služby.
Probne známé endpointy, **lokální** spadlé služby restartne (systemd / docker / launchd),
**cloud** služby (n8n, Home Assistant) jen reportne s konkrétní akcí, ověří iDoklad creds,
zaloguje a pošle Telegram notifikaci.

## Použití

```bash
./elias_mcp_heal.sh --report        # JEN probe, nic nerestartuje – spusť poprvé!
./elias_mcp_heal.sh                 # heal once: probe + restart lokálních + report
./elias_mcp_heal.sh --install-timer # nainstaluje self-heal (systemd timer / LaunchAgent)
./elias_mcp_heal.sh --help          # nápověda
```

**Exit code:** `0` = lokální služby OK, `1` = něco lokálního pořád DOWN/DEGRADED (pro alerting),
`2` = neznámý argument.

## Konfigurace přes env (nebo `.env`)

| Proměnná | Default | Význam |
|----------|---------|--------|
| `ELIAS_ENV_FILE` | `$HOME/.env` | cesta k `.env` s creds |
| `ELIAS_LOG_DIR` | `$HOME/elias/logs` | adresář pro log (`mcp_heal.log`) |
| `ELIAS_HEAL_INTERVAL_MIN` | `5` | interval self-healu (timer) |
| `ELIAS_AUTO_DISCOVER` | `1` | `1` = restartuj match-nuté služby dle vzorů, `0` = jen explicit list |
| `TELEGRAM_BOT_TOKEN` | – | bez tokenu se notifikace neposílá |
| `TELEGRAM_CHAT_ID` | – | cílový chat (nastav přes env, **nedávej do gitu**) |
| `IDOKLAD_CLIENT_ID` / `IDOKLAD_CLIENT_SECRET` | – | creds pro iDoklad token check |

Endpointy, explicitní služby k restartu a vzory pro auto-discovery se ladí přímo
v sekci `CONFIG` ve skriptu.

## Poznámky

- **Žádné tajné údaje nepatří do skriptu ani do gitu** — všechno přes `.env` (mimo repo).
- Klasifikace stavu: `UP` (2xx/3xx/4xx — server odpovídá), `AUTH` (401/403),
  `DEGRADED` (5xx), `DOWN` (spojení selhalo).
- Idempotentní, bezpečné pro cron/timer.
- macOS (bash 3.2) je podporovaný — fallback bez `mapfile`.
