#!/bin/bash
# Oprava Cloudflare Error 1033 (tunel nedostupný) – spustit na Mac mini (192.168.1.43).
# Restartuje cloudflared, ověří připojení tunelu a ukáže poslední řádky logu.
set -u
HOST="${1:-citoliby.investimenti.cz}"

say(){ printf '\n== %s\n' "$*"; }

say "cloudflared binárka"
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared chybí -> instaluji přes Homebrew"
  brew install cloudflared || { echo "Instalace selhala."; exit 1; }
fi
cloudflared --version

say "Stav služby před opravou"
sudo launchctl list 2>/dev/null | grep -i cloudflare || echo "(systémová launchd služba nenalezena)"
launchctl list 2>/dev/null | grep -i cloudflare || echo "(uživatelská launchd služba nenalezena)"
brew services list 2>/dev/null | grep -i cloudflared || echo "(brew služba nenalezena)"

say "Restart"
RESTARTED=0
if sudo launchctl list 2>/dev/null | grep -q com.cloudflare.cloudflared; then
  sudo launchctl kickstart -k system/com.cloudflare.cloudflared && RESTARTED=1
elif launchctl list 2>/dev/null | grep -q com.cloudflare.cloudflared; then
  launchctl kickstart -k "gui/$(id -u)/com.cloudflare.cloudflared" && RESTARTED=1
elif brew services list 2>/dev/null | grep -q cloudflared; then
  brew services restart cloudflared && RESTARTED=1
fi

if [ "$RESTARTED" = 0 ]; then
  echo "Žádná služba cloudflared není nainstalovaná -> instaluji jako systémovou službu."
  if [ -f "$HOME/.cloudflared/config.yml" ] || [ -f /etc/cloudflared/config.yml ]; then
    sudo cloudflared service install && RESTARTED=1
  else
    echo "Chybí config i token tunelu. Vezmi token z Cloudflare Zero Trust -> Networks -> Tunnels"
    echo "a spusť:  sudo cloudflared service install <TOKEN>"
    exit 2
  fi
fi

say "Čekám 10 s na navázání tunelu"
sleep 10

say "Stav tunelů (sloupec CONNECTIONS musí být neprázdný)"
cloudflared tunnel list 2>/dev/null || echo "(cloudflared tunnel list nedostupný – tunel běží přes token, kontrola níže)"

say "Poslední log"
for f in /Library/Logs/com.cloudflare.cloudflared.err.log /Library/Logs/com.cloudflare.cloudflared.out.log \
         "$HOME/Library/Logs/com.cloudflare.cloudflared.err.log" /opt/homebrew/var/log/cloudflared.log; do
  [ -f "$f" ] && { echo "-- $f"; tail -n 15 "$f"; }
done

say "Test z internetu: https://$HOST"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "https://$HOST/")
case "$CODE" in
  200|30*) echo "OK ($CODE) – Cloudflare odpovídá, tunel je nahoře.";;
  530)     echo "Stále Error 1033/530 – tunel se nepřipojil. Zkontroluj log výše a síť Macu."; exit 3;;
  *)       echo "Odpověď $CODE – zkontroluj log výše.";;
esac
