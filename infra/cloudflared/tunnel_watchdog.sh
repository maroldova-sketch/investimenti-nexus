#!/bin/bash
# Tunnel watchdog (LaunchDaemon, každé 2 min, běží jako root).
# Zkontroluje z internetu všechny 3 hostnames tunelu maroldova-hq. 530 = Cloudflare Error 1033
# (žádný connector) → kickstart daemonu cloudflared. Při 52x (origin) kickstartne i app agenty.
set -u
HOSTS="citoliby.investimenti.cz citoliby-data.investimenti.cz citoliby-archiv.investimenti.cz"
DAEMON="system/cz.investimenti.cloudflared-maroldova"
USER_UID=$(id -u investimenti)
APPS="cz.investimenti.citoliby.d cz.investimenti.citoliby.data cz.investimenti.citoliby-archiv"
STATE=/var/tmp/tunnel_watchdog.state
LOG="/Users/investimenti/andrew_core/logs/tunnel_watchdog.log"
ts(){ date '+%Y-%m-%d %H:%M:%S'; }
log(){ echo "$(ts) $*" >> "$LOG"; }

dead=0; origin=0; codes=""
for h in $HOSTS; do
  c=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "https://$h/" || echo 000)
  codes="$codes $h=$c"
  case "$c" in
    530) dead=$((dead+1));;
    52[0-9]) origin=$((origin+1));;
  esac
done

if [ "$dead" -gt 0 ]; then
  n=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$STATE"
  log "TUNEL DOLE ($dead/3, pokus $n):$codes → kickstart $DAEMON"
  launchctl kickstart -k "$DAEMON" 2>>"$LOG"
  if [ "$n" -ge 3 ]; then
    # 3× po sobě: zkus i starý uživatelský agent, kdyby daemon nebyl načtený
    launchctl kickstart -k "gui/$USER_UID/com.cloudflared.tunnel" 2>/dev/null
    log "eskalace: kickstart gui/$USER_UID/com.cloudflared.tunnel"
  fi
  exit 0
fi

if [ "$origin" -gt 0 ]; then
  log "ORIGIN DOLE ($origin/3):$codes → kickstart app agentů"
  for a in $APPS; do launchctl kickstart -k "gui/$USER_UID/$a" 2>>"$LOG"; done
  exit 0
fi

[ -f "$STATE" ] && { log "OK zpět:$codes"; rm -f "$STATE"; }
exit 0
