#!/bin/bash
# Instalace odolného tunelu maroldova-hq na Mac mini .43. Spustit: sudo bash install_mac.sh
# Idempotentní. Záloha → pmset (žádný spánek) → LaunchDaemon cloudflared + watchdog
# → vypnutí starého uživatelského agenta → ověření z internetu → při selhání rollback.
set -u
[ "$(id -u)" = 0 ] || { echo "Spusť přes sudo."; exit 1; }
SRC="$(cd "$(dirname "$0")" && pwd)"
U=investimenti; H=/Users/$U; UID_U=$(id -u $U)
CORE=$H/andrew_core
RUN=$CORE/runtime/hub/run_cloudflared_maroldova.sh
OLD_AGENT=com.cloudflared.tunnel
D1=cz.investimenti.cloudflared-maroldova
D2=cz.investimenti.tunnel-watchdog
LD=/Library/LaunchDaemons
BK=$CORE/_archive/tunnel_infra_backup_$(date +%Y%m%d-%H%M%S)
say(){ printf '\n== %s\n' "$*"; }
probe(){ curl -s -o /dev/null -w '%{http_code}' -m 15 https://citoliby.investimenti.cz/ || echo 000; }

say "0/6 preflight"
[ -f "$RUN" ] || { echo "STOP: chybí $RUN"; exit 1; }
command -v cloudflared >/dev/null || { echo "STOP: cloudflared není v PATH"; exit 1; }
echo "stav před: citoliby=$(probe)"

say "1/6 záloha → $BK"
mkdir -p "$BK" "$CORE/logs" "$CORE/runtime/watchdog"
cp -a "$H/Library/LaunchAgents/$OLD_AGENT.plist" "$BK/" 2>/dev/null || true
for d in $D1 $D2; do cp -a "$LD/$d.plist" "$BK/" 2>/dev/null || true; done
pmset -g custom > "$BK/pmset_before.txt"
chown -R $U:staff "$BK"

say "2/6 Mac nesmí spát"
pmset -a sleep 0 disksleep 0 standby 0 autopoweroff 0 womp 1 autorestart 1 powernap 0

say "3/6 soubory"
install -m 755 -o $U -g staff "$SRC/tunnel_watchdog.sh" "$CORE/runtime/watchdog/tunnel_watchdog.sh"
install -m 644 -o root -g wheel "$SRC/$D1.plist" "$LD/$D1.plist"
install -m 644 -o root -g wheel "$SRC/$D2.plist" "$LD/$D2.plist"
plutil -lint "$LD/$D1.plist" "$LD/$D2.plist" || { echo "STOP: plist je rozbitý"; exit 1; }

say "4/6 start daemonů"
launchctl bootout "system/$D1" 2>/dev/null; launchctl bootout "system/$D2" 2>/dev/null
launchctl bootstrap system "$LD/$D1.plist" && launchctl enable "system/$D1"
launchctl bootstrap system "$LD/$D2.plist" && launchctl enable "system/$D2"
sleep 15
launchctl print "system/$D1" | grep -E "state|pid" | head -3

say "5/6 starý uživatelský agent $OLD_AGENT → vypnout (daemon ho nahrazuje)"
launchctl bootout "gui/$UID_U/$OLD_AGENT" 2>/dev/null
launchctl disable "gui/$UID_U/$OLD_AGENT" 2>/dev/null
sleep 10

say "6/6 ověření z internetu"
for i in 1 2 3 4 5 6; do c=$(probe); echo "pokus $i: citoliby=$c"; case "$c" in 200|30*) break;; esac; sleep 10; done
case "$c" in
  200|30*)
    echo; echo "HOTOVO: tunel jede přes LaunchDaemon $D1, watchdog $D2 každé 2 min, Mac nespí."
    echo "Záloha: $BK"; exit 0;;
  *)
    echo; echo "!! ROLLBACK: tunel po instalaci neodpovídá ($c)"
    launchctl bootout "system/$D1" 2>/dev/null; launchctl bootout "system/$D2" 2>/dev/null
    rm -f "$LD/$D1.plist" "$LD/$D2.plist"
    launchctl enable "gui/$UID_U/$OLD_AGENT"; launchctl bootstrap "gui/$UID_U" "$H/Library/LaunchAgents/$OLD_AGENT.plist" 2>/dev/null
    launchctl kickstart -k "gui/$UID_U/$OLD_AGENT" 2>/dev/null
    sleep 15; echo "po rollbacku: citoliby=$(probe)"; exit 2;;
esac
