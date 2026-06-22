#!/usr/bin/env bash
# =====================================================================
# verify_external.sh — T5. Ověření ZVENKU (spouštěj mimo LAN/Tailnet!).
# Probne veřejné MCP endpointy + Bible smoke POST /sessions. Volitelně
# s tokenem (Bearer / token-v-URL). Píše PASS/FAIL.
#
#   ./tools/gateway/verify_external.sh
#   GATEWAY_TOKEN=xxx ./tools/gateway/verify_external.sh
#
# Pozn.: pouštěj z mobilní sítě / jiného serveru, NE z VPS ani z Tailnetu —
# jinak netestuješ reálnou veřejnou cestu.
# =====================================================================
set -uo pipefail
ENV_FILE="${ANDREW_ENV:-$HOME/andrew/.env}"
[[ -f "$ENV_FILE" ]] && { set -a; . "$ENV_FILE" 2>/dev/null || true; set +a; }
CF_ZONE="${CF_ZONE:-investimenti.cz}"
TOK="${GATEWAY_TOKEN:-}"

GRN=$'\033[32m'; RED=$'\033[31m'; RST=$'\033[0m'
fail=0
hdr=(); [[ -n "$TOK" ]] && hdr=(-H "Authorization: Bearer $TOK")

# varování když jsme v Tailnetu
if command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
  echo "⚠ POZOR: tenhle node je v Tailnetu — výsledek nemusí odrážet veřejnou cestu!"
fi

check(){ # název URL očekávaný-prefix [extra curl args...]
  local name="$1" url="$2" exp="$3"; shift 3
  local c; c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${hdr[@]}" "$@" "$url" 2>/dev/null)
  [[ "$c" =~ ^[0-9]{3}$ ]] || c=000
  if [[ "$c" == $exp* ]]; then echo "  ${GRN}PASS${RST} $name → HTTP $c ($url)"
  else echo "  ${RED}FAIL${RST} $name → HTTP $c (čekáno ${exp}x) ($url)"; fail=1; fi
}

echo "════ verify_external @ $(hostname) $(date '+%F %T') ════"
# bez tokenu MUSÍ být 401/403 (pokud je brána chráněná); s tokenem 2xx
if [[ -z "$TOK" ]]; then
  echo "── bez tokenu (čekám 401/403 pokud je auth zapnutá) ──"
  check "bible-mcp (no-auth)" "https://bible-mcp.$CF_ZONE/health" "4"
  check "nexus-mcp (no-auth)" "https://nexus-mcp.$CF_ZONE/health" "4"
else
  echo "── s tokenem (čekám 2xx) ──"
  check "bible-mcp" "https://bible-mcp.$CF_ZONE/health" "2"
  check "nexus-mcp" "https://nexus-mcp.$CF_ZONE/health" "2"
  # Bible smoke: POST /sessions
  c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${hdr[@]}" -X POST \
      -H 'Content-Type: application/json' -d '{}' "https://bible-mcp.$CF_ZONE/sessions" 2>/dev/null)
  [[ "$c" =~ ^2 ]] && echo "  ${GRN}PASS${RST} bible POST /sessions → $c" \
                   || { echo "  ${RED}FAIL${RST} bible POST /sessions → $c"; fail=1; }
fi

echo
[[ "$fail" == "0" ]] && echo "${GRN}✓ vše OK${RST}" || echo "${RED}✗ něco selhalo${RST}"
exit $fail
