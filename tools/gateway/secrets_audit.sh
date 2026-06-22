#!/usr/bin/env bash
# =====================================================================
# secrets_audit.sh — T0. Kde leží secrets. JEN NÁZVY KLÍČŮ, NIKDY HODNOTY.
# Spouštěj na Macu .43 (kde žijí trezory). Bezpečné do logu i do chatu —
# netiskne žádnou hodnotu, jen jména proměnných / klíčů a existenci souborů.
#
#   ./tools/gateway/secrets_audit.sh
#
# Ověří dostupnost klíčů potřebných pro bránu (CF API, Tailscale, HA) a
# řekne, co chybí (→ co vygenerovat). Nic nemění.
# =====================================================================
set -uo pipefail
have(){ command -v "$1" >/dev/null 2>&1; }
ANDREW_ENV="${ANDREW_ENV:-$HOME/andrew/.env}"
SECRETS_JSON="${SECRETS_JSON:-$HOME/andrew/secrets/secrets.json}"
CORE_ENV1="$HOME/andrew_core/.env"
CORE_ENV2="$HOME/andrew_core/config/.env"

names_env(){ [[ -f "$1" ]] && grep -oE '^[A-Z0-9_]+=' "$1" 2>/dev/null | tr -d '=' | sort -u; }

echo "════ secrets_audit @ $(hostname) $(date '+%F %T') — JEN NÁZVY ════"

for f in "$ANDREW_ENV" "$CORE_ENV1" "$CORE_ENV2"; do
  echo "── $f ──"
  if [[ -f "$f" ]]; then
    perm=$(stat -f '%Lp' "$f" 2>/dev/null || stat -c '%a' "$f" 2>/dev/null)
    echo "   existuje (chmod $perm); klíče:"
    names_env "$f" | sed 's/^/     /'
  else
    echo "   (chybí)"
  fi
done

echo "── $SECRETS_JSON ──"
if [[ -f "$SECRETS_JSON" ]]; then
  if have jq; then jq -r 'keys[]' "$SECRETS_JSON" 2>/dev/null | sed 's/^/     /'
  else echo "     (nainstaluj jq pro výpis klíčů)"; fi
else
  echo "   (chybí)"
fi

echo
echo "── potřebné pro bránu (existence, ne hodnota) ──"
need(){ # popis  regex
  local desc="$1" rx="$2" hit=""
  hit=$(grep -lE "$rx" "$ANDREW_ENV" "$CORE_ENV1" "$CORE_ENV2" 2>/dev/null | head -1)
  [[ -z "$hit" && -f "$SECRETS_JSON" ]] && have jq && jq -e --arg rx "$rx" 'to_entries|map(select(.key|test($rx)))|length>0' "$SECRETS_JSON" >/dev/null 2>&1 && hit="$SECRETS_JSON"
  if [[ -n "$hit" ]]; then echo "   ✓ $desc — nalezeno v $hit"
  else echo "   ✗ $desc — CHYBÍ → vygeneruj"; fi
}
need "CF API token (Zone:DNS:Edit + Account:Tunnel)" 'CF_API|CLOUDFLARE_API|CF_TOKEN'
need "M365 (tenant/client/secret)"                   'M365_|GRAPH_|TENANT'
need "HA long-lived token"                           'HA_TOKEN|HASS|SUPERVISOR'

echo
echo "── infra ──"
have tailscale  && { echo "   tailscale: $(tailscale status --json 2>/dev/null | { have jq && jq -r .BackendState || echo '?'; })"; } || echo "   tailscale: chybí"
have cloudflared && { echo "   cloudflared tunely:"; cloudflared tunnel list 2>/dev/null | sed 's/^/     /' | head; } || echo "   cloudflared: chybí"
echo "   ~/.cloudflared/:"; ls "$HOME/.cloudflared/" 2>/dev/null | sed 's/^/     /' || echo "     (nic)"

echo
echo "Hotovo. Chybějící (✗) doplň: CF token, TS auth key, HA token — pak spusť discover.sh / setup_gateway.sh."
