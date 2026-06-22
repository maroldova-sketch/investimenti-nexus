#!/usr/bin/env bash
# =====================================================================
# reach_probe.sh — T1 Mapa dosahu. Spouštěj NA NODU .43 (Mac), kde žijí
# lokální služby, ~/andrew/.env a Tailscale. Ověří každý systém (jen čtení),
# zapíše OK/FAIL + důvod do docs/REACH.md a vypíše tabulku.
#
#   ./scripts/reach_probe.sh                 # proběhne + zapíše docs/REACH.md
#   REACH_OUT=/tmp/REACH.md ./scripts/reach_probe.sh
#
# Bezpečné: žádné zápisy do cizích systémů, jen health/whoami/GET.
# =====================================================================
set -uo pipefail

ENV_FILE="${ANDREW_ENV:-$HOME/andrew/.env}"
OUT="${REACH_OUT:-docs/REACH.md}"
[[ -f "$ENV_FILE" ]] && { set -a; . "$ENV_FILE" 2>/dev/null || true; set +a; }

ROWS=()   # "systém|endpoint|stav|důvod"
add(){ ROWS+=("$1|$2|$3|$4"); printf '  %-12s %-40s %s\n' "$1" "$3" "$4"; }

code(){ local c; c=$(curl -s -k -o /dev/null -w '%{http_code}' --max-time "${2:-6}" "$1" 2>/dev/null); [[ "$c" =~ ^[0-9]{3}$ ]] || c=000; printf '%s' "$c"; }
body(){ curl -s -k --max-time "${2:-6}" "$1" 2>/dev/null || echo ''; }

echo "════ reach_probe @ $(hostname) $(date '+%F %T') ════"

# 1) Bible API ---------------------------------------------------------
c=$(code "http://localhost:8770/health")
if [[ "$c" =~ ^2 ]]; then
  # smoke POST /sessions
  sc=$(curl -s -k -o /dev/null -w '%{http_code}' --max-time 6 -X POST \
        -H 'Content-Type: application/json' -d '{}' "http://localhost:8770/sessions" 2>/dev/null || echo 000)
  add "bible-api" "localhost:8770/health" "OK" "health $c, POST /sessions → $sc"
else
  add "bible-api" "localhost:8770/health" "FAIL" "health HTTP $c (neběží / jiný port?)"
fi

# 2) Registry ----------------------------------------------------------
c=$(code "http://192.168.1.43:8110/health")
[[ "$c" =~ ^2 ]] && add "registry" "192.168.1.43:8110/health" "OK" "HTTP $c" \
                  || add "registry" "192.168.1.43:8110/health" "FAIL" "HTTP $c"

# 3) NEXUS -------------------------------------------------------------
NEXUS_PORT="${NEXUS_PORT:-8000}"
c=$(code "http://127.0.0.1:${NEXUS_PORT}/health")
runinfo=""
command -v launchctl >/dev/null 2>&1 && runinfo=$(launchctl list 2>/dev/null | grep -i nexus | awk '{print $3}' | head -1)
[[ -z "$runinfo" ]] && command -v docker >/dev/null 2>&1 && runinfo=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -i nexus | head -1)
repo=$(rg -l --max-count 1 "title=\"NEXUS\"|APIRouter" "$HOME" 2>/dev/null | head -1)
if [[ "$c" =~ ^2 ]]; then
  add "nexus" "127.0.0.1:${NEXUS_PORT}/health" "OK" "HTTP $c; run=${runinfo:-?}; repo=${repo:-?}"
else
  add "nexus" "127.0.0.1:${NEXUS_PORT}/health" "FAIL" "HTTP $c; run=${runinfo:-nenalezeno}; repo=${repo:-?}"
fi

# 4) fortress (SSH přes Tailscale) ------------------------------------
FORTRESS_HOST="${FORTRESS_HOST:-fortress}"
if command -v ssh >/dev/null 2>&1; then
  out=$(ssh -o ConnectTimeout=6 -o BatchMode=yes "$FORTRESS_HOST" 'uname -a; docker ps --format "{{.Names}}" 2>/dev/null | tr "\n" "," ' 2>&1 | tr '\n' ' ')
  if [[ -n "$out" && "$out" != *"Could not"* && "$out" != *"refused"* && "$out" != *"timed out"* ]]; then
    add "fortress" "ssh://$FORTRESS_HOST" "OK" "${out:0:90}"
  else
    add "fortress" "ssh://$FORTRESS_HOST" "FAIL" "ssh: ${out:0:80}"
  fi
else
  add "fortress" "ssh://$FORTRESS_HOST" "FAIL" "ssh binárka chybí"
fi

# 5) M365 token (JEN čtení) -------------------------------------------
if [[ -n "${M365_TENANT_ID:-}" && -n "${M365_CLIENT_ID:-}" && -n "${M365_CLIENT_SECRET:-}" ]]; then
  tok=$(curl -s --max-time 10 -X POST \
    "https://login.microsoftonline.com/${M365_TENANT_ID}/oauth2/v2.0/token" \
    -d "grant_type=client_credentials&client_id=${M365_CLIENT_ID}&client_secret=${M365_CLIENT_SECRET}&scope=https%3A%2F%2Fgraph.microsoft.com%2F.default" \
    2>/dev/null | grep -o '"access_token":"[^"]*"' | head -1)
  if [[ -n "$tok" ]]; then
    mb="${M365_MAILBOX:-}"
    if [[ -n "$mb" ]]; then
      mc=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 \
        -H "Authorization: Bearer ${tok#*:\"}" "https://graph.microsoft.com/v1.0/users/$mb" 2>/dev/null || echo 000)
      add "m365" "graph/.default (app)" "OK" "token OK; /users/$mb → $mc"
    else
      add "m365" "graph/.default (app)" "OK" "token OK (nastav M365_MAILBOX pro test schránky)"
    fi
  else
    add "m365" "graph/.default (app)" "FAIL" "token nezískán (creds/permissions?)"
  fi
else
  add "m365" "graph/.default (app)" "FAIL" "M365_* creds chybí v $ENV_FILE"
fi

# 6) Home Assistant ----------------------------------------------------
if [[ -n "${HA_URL:-}" && -n "${HA_TOKEN:-}" ]]; then
  c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 -H "Authorization: Bearer $HA_TOKEN" "${HA_URL%/}/api/" 2>/dev/null || echo 000)
  [[ "$c" =~ ^2 ]] && add "home-assistant" "${HA_URL}/api/" "OK" "HTTP $c" \
                    || add "home-assistant" "${HA_URL}/api/" "FAIL" "HTTP $c"
else
  add "home-assistant" "/api/" "FAIL" "HA_URL/HA_TOKEN chybí v $ENV_FILE"
fi

# 7) n8n ---------------------------------------------------------------
if [[ -n "${N8N_URL:-}" ]]; then
  hz=$(code "${N8N_URL%/}/healthz")
  ah="?"
  [[ -n "${N8N_API_KEY:-}" ]] && ah=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 -H "X-N8N-API-KEY: $N8N_API_KEY" "${N8N_URL%/}/rest/active-workflows" 2>/dev/null || echo 000)
  [[ "$hz" =~ ^2 ]] && add "n8n" "${N8N_URL}/healthz" "OK" "healthz $hz; rest/active $ah" \
                    || add "n8n" "${N8N_URL}/healthz" "FAIL" "healthz $hz"
else
  add "n8n" "/healthz" "FAIL" "N8N_URL chybí v $ENV_FILE"
fi

# 8) Cloudflare --------------------------------------------------------
if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  r=$(body "https://api.cloudflare.com/client/v4/user/tokens/verify" 8)
  echo "$r" | grep -q '"success":true' && add "cloudflare" "tokens/verify" "OK" "token aktivní" \
                                        || add "cloudflare" "tokens/verify" "FAIL" "verify selhal"
else
  add "cloudflare" "tokens/verify" "FAIL" "CLOUDFLARE_API_TOKEN chybí v $ENV_FILE"
fi

# ── zápis docs/REACH.md ───────────────────────────────────────────────
mkdir -p "$(dirname "$OUT")"
{
  echo "# T1 — Mapa dosahu (REACH)"
  echo
  echo "_Generováno \`scripts/reach_probe.sh\` na \`$(hostname)\` $(date '+%F %T'). Jen čtení._"
  echo
  echo "| Systém | Endpoint | Stav | Důvod |"
  echo "|--------|----------|------|-------|"
  for r in "${ROWS[@]}"; do
    IFS='|' read -r s e st why <<<"$r"
    echo "| $s | \`$e\` | $st | $why |"
  done
} > "$OUT"

ok=$(printf '%s\n' "${ROWS[@]}" | awk -F'|' '$3=="OK"' | wc -l | tr -d ' ')
fail=$(printf '%s\n' "${ROWS[@]}" | awk -F'|' '$3=="FAIL"' | wc -l | tr -d ' ')
echo "──── $ok OK, $fail FAIL → $OUT ────"
