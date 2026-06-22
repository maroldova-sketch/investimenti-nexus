#!/usr/bin/env bash
# =====================================================================
# setup_gateway.sh — T2/T4. Idempotentní brána na VPS.
# Postaví/aktualizuje cloudflared named tunnel + ingress routy:
#   bible-mcp.investimenti.cz → http://<MAC>:8770   (Bible přes Tailscale, canon)
#   nexus-mcp.investimenti.cz → http://<MAC>:8791   (NEXUS MCP přes Tailscale)
# a přepojí DNS z mrtvého RPi (.220) na tento tunel.
#
# ZÁKON 9 — VPS = STATELESS, ŽÁDNÉ SECRETS:
#   • DNS routy + repoint (CF API) spouštěj NA MACu (.43), kde žije CF token.
#   • VPS drží jen cloudflared MANAGED TOKEN (v service), žádný .env, žádné klíče.
#   • INGRESS_MODE=managed (default): ingress se řídí přes CF dashboard/API, NE
#     config.yml na VPS. INGRESS_MODE=local jen pro lokálně spravovaný tunel.
#   • Tento skript NEKOPÍRUJE secrets na VPS.
#
# BEZPEČNĚ: default DRY-RUN (jen vypíše). Pro reálné změny přidej --apply.
# Mazání cizích DNS nedělá automaticky — jen navrhne (viz výstup).
#
#   ./tools/gateway/setup_gateway.sh                 # dry-run (na Macu)
#   ./tools/gateway/setup_gateway.sh --apply         # provede
#
# Konfig (env / ~/andrew/.env na Macu):
#   CLOUDFLARE_API_TOKEN (DNS:Edit + Tunnel:Edit), CF_ZONE, TUNNEL_NAME,
#   MAC_HOST (Tailscale MagicDNS Macu), BIBLE_PORT, NEXUS_MCP_PORT,
#   INGRESS_MODE=managed|local
# =====================================================================
set -uo pipefail

APPLY=0; [[ "${1:-}" == "--apply" ]] && APPLY=1
ENV_FILE="${ANDREW_ENV:-$HOME/andrew/.env}"
[[ -f "$ENV_FILE" ]] && { set -a; . "$ENV_FILE" 2>/dev/null || true; set +a; }

CF_ZONE="${CF_ZONE:-investimenti.cz}"
TUNNEL_NAME="${TUNNEL_NAME:-investimenti-gateway}"
MAC_HOST="${MAC_HOST:-}"
BIBLE_PORT="${BIBLE_PORT:-8770}"
NEXUS_MCP_PORT="${NEXUS_MCP_PORT:-8791}"
CFG_DIR="${CLOUDFLARED_DIR:-$HOME/.cloudflared}"
RPI_DEAD="${RPI_DEAD:-192.168.1.220}"
INGRESS_MODE="${INGRESS_MODE:-managed}"   # managed = ingress přes CF dashboard/API (VPS stateless); local = config.yml
CFAPI="https://api.cloudflare.com/client/v4"

# hostname → upstream (přes Tailscale na Mac)
declare -a HOSTS=(
  "bible-mcp.$CF_ZONE|http://$MAC_HOST:$BIBLE_PORT"
  "nexus-mcp.$CF_ZONE|http://$MAC_HOST:$NEXUS_MCP_PORT"
)

run(){ if [[ "$APPLY" == "1" ]]; then echo "  ▶ $*"; "$@"; else echo "  [dry-run] $*"; fi; }
die(){ echo "✗ $*" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }

echo "════ setup_gateway @ $(hostname) | apply=$APPLY ════"
have cloudflared || die "cloudflared není nainstalován"
[[ -n "$MAC_HOST" ]] || die "MAC_HOST (Tailscale MagicDNS Macu) není nastaven — nehádám ho"
mkdir -p "$CFG_DIR"

# 1) named tunnel (idempotentně) ----------------------------------------
echo "── tunnel '$TUNNEL_NAME' ──"
TID=$(cloudflared tunnel list -o json 2>/dev/null | { have jq && jq -r ".[] | select(.name==\"$TUNNEL_NAME\") | .id" || grep -o "$TUNNEL_NAME"; } | head -1)
if [[ -z "$TID" ]]; then
  echo "  tunnel neexistuje → vytvořím"
  run cloudflared tunnel create "$TUNNEL_NAME"
  TID=$(cloudflared tunnel list -o json 2>/dev/null | { have jq && jq -r ".[] | select(.name==\"$TUNNEL_NAME\") | .id" || echo "<new>"; } | head -1)
else
  echo "  ✓ tunnel existuje: $TID"
fi

# 2) ingress ------------------------------------------------------------
echo "── ingress (mode=$INGRESS_MODE) ──"
echo "  cílové routy:"
for row in "${HOSTS[@]}"; do IFS='|' read -r host up <<<"$row"; echo "    $host → $up"; done
if [[ "$INGRESS_MODE" == "local" ]]; then
  # jen pro lokálně spravovaný tunel (NE na stateless VPS)
  TMP_CFG=$(mktemp)
  {
    echo "tunnel: ${TID:-$TUNNEL_NAME}"
    echo "credentials-file: $CFG_DIR/${TID:-$TUNNEL_NAME}.json"
    echo "ingress:"
    for row in "${HOSTS[@]}"; do
      IFS='|' read -r host up <<<"$row"
      echo "  - hostname: $host"
      echo "    service: $up"
      echo "    originRequest: { noTLSVerify: true, connectTimeout: 10s }"
    done
    echo "  - service: http_status:404"
  } > "$TMP_CFG"
  echo "  navržený config.yml:"; sed 's/^/    /' "$TMP_CFG"
  if [[ "$APPLY" == "1" ]]; then cp "$TMP_CFG" "$CFG_DIR/config.yml"; echo "  ✓ zapsáno $CFG_DIR/config.yml"; else echo "  [dry-run]"; fi
  rm -f "$TMP_CFG"
else
  echo "  managed mode: ingress řiď přes CF dashboard / API pro tunel ${TID:-$TUNNEL_NAME}."
  echo "  VPS drží jen managed token — sem se config.yml se secrets NEzapisuje (Zákon 9)."
  echo "  API (spouštěj na Macu s CF tokenem):"
  echo "    PUT $CFAPI/accounts/<acc>/cfd_tunnel/${TID:-<id>}/configurations"
fi

# 3) DNS routy hostname → tunnel (idempotentně) -------------------------
echo "── DNS routy (CNAME → tunnel) ──"
for row in "${HOSTS[@]}"; do
  IFS='|' read -r host _ <<<"$row"
  run cloudflared tunnel route dns "$TUNNEL_NAME" "$host"
done

# 4) repoint / úklid mrtvého RPi (jen NÁVRH — mazání potvrď ručně) ------
echo "── kontrola mrtvého RPi ($RPI_DEAD) ──"
if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]] && have jq; then
  zid=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=$CF_ZONE" -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq -r '.result[0].id')
  recs=$(curl -s "https://api.cloudflare.com/client/v4/zones/$zid/dns_records?per_page=200" -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN")
  echo "$recs" | jq -r --arg ip "$RPI_DEAD" '.result[] | select(.content==$ip) | "\(.id)\t\(.name)\t\(.type)"' | while IFS=$'\t' read -r rid name typ; do
    [[ -z "$rid" ]] && continue
    echo "  ⚠ $name ($typ) → $RPI_DEAD (mrtvý)"
    if [[ "$APPLY" == "1" ]]; then
      echo "     ▶ MAŽU starý záznam $rid (repoint na tunel proběhl výše)"
      curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/$zid/dns_records/$rid" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq -r '"     výsledek: success=\(.success)"'
    else
      echo "     [dry-run] smazal bych $rid — over a spusť s --apply"
    fi
  done
else
  echo "  (CLOUDFLARE_API_TOKEN+jq potřeba pro detekci RPi záznamů)"
fi

echo
echo "Hotovo (apply=$APPLY). Spusť tunnel: cloudflared tunnel run $TUNNEL_NAME"
echo "Ověř zvenku: ./tools/gateway/verify_external.sh"
