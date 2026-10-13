# Tunel maroldova-hq – odolná infra (citoliby, citoliby-data, citoliby-archiv)

## Proč
Error 1033 = Cloudflare nemá žádný živý connector. Tunel dosud běžel jen jako uživatelský LaunchAgent
`com.cloudflared.tunnel` na Mac mini .43: umře při odhlášení, spánku, pádu GUI session, nikdo ho nekopne.

## Vrstvy
1. **Mac – LaunchDaemon** `cz.investimenti.cloudflared-maroldova`: systémová úroveň, běží jako uživatel
   `investimenti`, startuje při bootu před přihlášením, `KeepAlive`, používá stávající
   `runtime/hub/run_cloudflared_maroldova.sh` (token/config zůstávají kde jsou). `pmset` vypne spánek.
2. **Mac – watchdog** `cz.investimenti.tunnel-watchdog`: každé 2 min proklepne 3 hostnames z internetu.
   530 → kickstart daemonu (3× po sobě i starého agenta), 52x → kickstart app agentů. Log `logs/tunnel_watchdog.log`.
3. **Fortress – Uptime Kuma**: viz `uptime-kuma.md`, alert na Telegram když watchdog nestačil.
4. **RPi5 – replica connector** (`rpi5/`): druhý connector stejného tunelu na jiném stroji. Zapnout až po
   přepnutí appek na LAN bind.

## Instalace (Mac)
    sudo bash infra/cloudflared/install_mac.sh
Idempotentní, záloha do `~/andrew_core/_archive/tunnel_infra_backup_*`, při selhání vrátí starý agent.

## Rollback ručně
    sudo launchctl bootout system/cz.investimenti.cloudflared-maroldova
    sudo launchctl bootout system/cz.investimenti.tunnel-watchdog
    launchctl enable gui/$(id -u)/com.cloudflared.tunnel && launchctl kickstart -k gui/$(id -u)/com.cloudflared.tunnel

## Kontrola
    sudo launchctl print system/cz.investimenti.cloudflared-maroldova | grep -E 'state|pid'
    tail ~/andrew_core/logs/tunnel_watchdog.log
    curl -s -o /dev/null -w '%{http_code}\n' https://citoliby.investimenti.cz/   # 302 = OK
