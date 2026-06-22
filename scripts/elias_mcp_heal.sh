#!/usr/bin/env bash
# =====================================================================
# elias_mcp_heal.sh  —  Elias MCP / bridge health + self-heal
# ---------------------------------------------------------------------
# Spouštěj na nodu, kde běží MCP služby (Mac .43 canonical, fortress replica).
# Node-agnostic: probne známé endpointy, LOKÁLNÍ spadlé služby restartne,
# CLOUD (n8n, HA) jen reportne s přesnou akcí, ověří tokeny/creds,
# zaloguje a pingne Telegram. Idempotentní, bezpečné pro cron/timer.
#
# Použití:
#   ./elias_mcp_heal.sh              # heal once (probe + restart lokálních + report)
#   ./elias_mcp_heal.sh --report     # JEN probe, NIC nerestartuje (spusť poprvé!)
#   ./elias_mcp_heal.sh --install-timer   # nainstaluje self-heal (systemd timer / LaunchAgent) a skončí
#   ./elias_mcp_heal.sh --help       # nápověda
#
# Exit: 0 = lokální služby OK; !=0 = něco lokálního pořád DOWN/DEGRADED (pro alerting).
# =====================================================================
set -uo pipefail

### ===================== CONFIG (zkontroluj ↓) =====================
ENV_FILE="${ELIAS_ENV_FILE:-$HOME/.env}"          # ← cesta k .env (creds)
LOG_DIR="${ELIAS_LOG_DIR:-$HOME/elias/logs}"
INTERVAL_MIN="${ELIAS_HEAL_INTERVAL_MIN:-5}"      # interval self-healu v minutách
AUTO_DISCOVER="${ELIAS_AUTO_DISCOVER:-1}"         # 1 = restartuj match-nuté služby; 0 = jen explicit list níž

# Endpointy:  NÁZEV|URL|TYP(local|cloud)
ENDPOINTS=(
  "bible-mcp|https://bible-mcp.investimenti.cz/mcp|local"
  "bible-api-lan|http://192.168.1.43:8770/|local"
  "registry|http://192.168.1.43:8110/|local"
  "dave-bridge|http://127.0.0.1:8788/|local"
  "n8n-mcp|https://investimenti.app.n8n.cloud/mcp-server/http|cloud"
  "ha-klod-mcp|https://fhyoo45j4v2ldomehshuiodqgc6t4dse.ui.nabu.casa/|cloud"
)

# Explicitní služby k restartu (mají přednost před auto-discovery).
# Nech prázdné = použije se auto-discovery podle vzorů.
SERVICES_SYSTEMD=()        # např: ("bible-mcp.service" "cloudflared.service")
CONTAINERS_DOCKER=()       # např: ("bible-mcp" "dave-bridge")
LABELS_LAUNCHD=()          # macOS, např: ("cz.investimenti.bible-mcp")

# Vzory pro auto-discovery (konzervativní – ať nerestartuje cizí věci)
SVC_PATTERNS='bible[-_]?mcp|dave[-_]?bridge|registry|cloudflared'

# iDoklad creds check (uprav názvy proměnných, pokud máš jiné)
IDOKLAD_TOKEN_URL="${IDOKLAD_TOKEN_URL:-https://identity.idoklad.cz/server/connect/token}"
IDOKLAD_ID_VAR="${IDOKLAD_ID_VAR:-IDOKLAD_CLIENT_ID}"
IDOKLAD_SECRET_VAR="${IDOKLAD_SECRET_VAR:-IDOKLAD_CLIENT_SECRET}"
IDOKLAD_SCOPE="${IDOKLAD_SCOPE:-idoklad_api}"

# Telegram (z env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID). Bez tokenu/chat_id = ticho.
# Nedávej sem reálné chat_id natvrdo – nastav přes env / .env (ať neleží v gitu).
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# Registry: volitelný JSON katalog endpointů (přepíše/rozšíří ENDPOINTS výše).
# Formát: [{"name":"x","url":"https://...","type":"local|cloud"}, ...]
ELIAS_REGISTRY_FILE="${ELIAS_REGISTRY_FILE:-$HOME/elias/registry.json}"

# Nexus API: zápis výpadků do Nexus notifikací (potřebuje token se scope notify:write).
NEXUS_API_BASE="${NEXUS_API_BASE:-}"            # např. https://nexus.investimenti.cz
NEXUS_API_KEY="${NEXUS_API_KEY:-}"              # nxs_... (scripts/nexus_token.py)
### ================================================================

LOG_FILE="$LOG_DIR/mcp_heal.log"
mkdir -p "$LOG_DIR" 2>/dev/null || true
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

SUDO=""
[[ $EUID -ne 0 ]] && command -v sudo >/dev/null 2>&1 && SUDO="sudo -n"

C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_RED=$'\033[31m'; C_RST=$'\033[0m'
SUMMARY=""; FAIL_LOCAL=0; ACTIONS=""

log(){ printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG_FILE"; }
note(){ SUMMARY+="$1"$'\n'; }
act(){ ACTIONS+="• $1"$'\n'; }

# --- načti .env (bezpečně i pod set -u) ---
load_env(){
  if [[ -f "$ENV_FILE" ]]; then
    set +u; set -a; . "$ENV_FILE" 2>/dev/null || true; set +a; set -u
    log "✓ .env načten: $ENV_FILE"
  else
    log "${C_YEL}! .env nenalezen: $ENV_FILE${C_RST}"
    note "⚠ .env chybí ($ENV_FILE)"
  fi
}

# Vrátí přesně 3místný HTTP kód; selhání spojení / nedostupný curl → 000.
# (curl při selhání spojení vytiskne "000" a zároveň skončí nenulově – proto
#  nesmíme řetězit `|| echo 000`, jinak vznikne "000000" a classify ho vezme jako UP.)
http_code(){
  local code
  code=$(curl -sS -k -L -o /dev/null -w '%{http_code}' --max-time 8 "$1" 2>/dev/null)
  [[ "$code" =~ ^[0-9]{3}$ ]] || code=000
  printf '%s' "$code"
}

# klasifikace: UP / AUTH / DEGRADED / DOWN
classify(){
  local code="$1"
  case "$code" in
    000)             echo DOWN ;;
    401|403)         echo AUTH ;;
    5[0-9][0-9])     echo DEGRADED ;;
    *)               echo UP ;;   # 2xx/3xx/4xx = server odpovídá
  esac
}

probe_all(){
  log "── PROBE ──────────────────────────────────────────"
  for row in "${ENDPOINTS[@]}"; do
    IFS='|' read -r name url typ <<<"$row"
    local code st col
    code=$(http_code "$url"); st=$(classify "$code")
    case "$st" in UP) col=$C_GRN;; AUTH) col=$C_YEL;; *) col=$C_RED;; esac
    log "  ${col}${st}${C_RST}  $name  (HTTP $code, $typ)  $url"
    note "$st  $name ($typ, HTTP $code)"

    if [[ "$st" == "AUTH" ]]; then
      if [[ "$typ" == "cloud" ]]; then
        act "$name: AUTH → reconnect v Claude appce (Settings → Connectors → reconnect; vyhořelej OAuth token)"
      else
        act "$name: AUTH → ověř token v $ENV_FILE / reauth lokálně"
      fi
    elif [[ "$st" == "DOWN" || "$st" == "DEGRADED" ]]; then
      if [[ "$typ" == "cloud" ]]; then
        act "$name: $st → cloud služba, nedá se restartnout odsud; zkontroluj stav providera (n8n cloud / Nabu Casa)"
      else
        FAIL_LOCAL=1
        act "$name: $st → lokální, zkusím restart služby"
      fi
    fi
  done
}

restart_systemd(){
  command -v systemctl >/dev/null 2>&1 || return 0
  local units=(); units=(${SERVICES_SYSTEMD[@]+"${SERVICES_SYSTEMD[@]}"})
  if [[ ${#units[@]} -eq 0 && "$AUTO_DISCOVER" == "1" ]]; then
    mapfile -t units < <($SUDO systemctl list-unit-files --type=service --no-legend 2>/dev/null \
                          | awk '{print $1}' | grep -Ei "$SVC_PATTERNS")
  fi
  for u in ${units[@]+"${units[@]}"}; do
    [[ -z "$u" ]] && continue
    local state; state=$($SUDO systemctl is-active "$u" 2>/dev/null || echo unknown)
    if [[ "$state" != "active" ]]; then
      log "  ${C_YEL}↻ systemd $u = $state → restart${C_RST}"
      if $SUDO systemctl restart "$u" 2>>"$LOG_FILE"; then act "restart OK: $u"; else act "restart SELHAL: $u"; fi
    fi
  done
}

restart_docker(){
  command -v docker >/dev/null 2>&1 || return 0
  local names=(); names=(${CONTAINERS_DOCKER[@]+"${CONTAINERS_DOCKER[@]}"})
  if [[ ${#names[@]} -eq 0 && "$AUTO_DISCOVER" == "1" ]]; then
    mapfile -t names < <($SUDO docker ps -a --format '{{.Names}} {{.Status}}' 2>/dev/null \
                          | grep -Ei "$SVC_PATTERNS" | grep -vi '^.* Up' | awk '{print $1}')
  fi
  for c in ${names[@]+"${names[@]}"}; do
    [[ -z "$c" ]] && continue
    local status; status=$($SUDO docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo gone)
    if [[ "$status" != "running" ]]; then
      log "  ${C_YEL}↻ docker $c = $status → restart${C_RST}"
      if $SUDO docker restart "$c" >/dev/null 2>&1; then act "restart OK: docker/$c"; else act "restart SELHAL: docker/$c"; fi
    fi
  done
}

restart_launchd(){   # macOS (Mac .43)
  command -v launchctl >/dev/null 2>&1 || return 0
  local labels=(); labels=(${LABELS_LAUNCHD[@]+"${LABELS_LAUNCHD[@]}"})
  if [[ ${#labels[@]} -eq 0 && "$AUTO_DISCOVER" == "1" ]]; then
    # macOS ships bash 3.2 bez `mapfile` → fallback na read-loop
    if command -v mapfile >/dev/null 2>&1; then
      mapfile -t labels < <(launchctl list 2>/dev/null | awk '{print $3}' | grep -Ei "$SVC_PATTERNS")
    else
      while IFS= read -r _l; do [[ -n "$_l" ]] && labels+=("$_l"); done \
        < <(launchctl list 2>/dev/null | awk '{print $3}' | grep -Ei "$SVC_PATTERNS")
    fi
  fi
  for l in ${labels[@]+"${labels[@]}"}; do
    [[ -z "$l" ]] && continue
    log "  ${C_YEL}↻ launchd $l → kickstart -k${C_RST}"
    if launchctl kickstart -k "gui/$(id -u)/$l" 2>>"$LOG_FILE"; then act "kickstart OK: $l"; else act "kickstart SELHAL: $l"; fi
  done
  # cloudflared přes brew services (fallback)
  if command -v brew >/dev/null 2>&1 && brew services list 2>/dev/null | grep -qi cloudflared; then
    brew services restart cloudflared >/dev/null 2>&1 && act "brew restart: cloudflared" || true
  fi
}

heal_local(){
  log "── HEAL (lokální) ────────────────────────────────"
  restart_systemd
  restart_docker
  restart_launchd
  log "  …pauza 4s, re-probe lokálních"
  sleep 4
  FAIL_LOCAL=0
  for row in "${ENDPOINTS[@]}"; do
    IFS='|' read -r name url typ <<<"$row"
    [[ "$typ" == "local" ]] || continue
    local st; st=$(classify "$(http_code "$url")")
    [[ "$st" == "DOWN" || "$st" == "DEGRADED" ]] && { FAIL_LOCAL=1; log "  ${C_RED}stále $st: $name${C_RST}"; }
  done
}

check_idoklad(){
  local id sec; id="${!IDOKLAD_ID_VAR:-}"; sec="${!IDOKLAD_SECRET_VAR:-}"
  if [[ -z "$id" || -z "$sec" ]]; then
    log "${C_YEL}! iDoklad creds ($IDOKLAD_ID_VAR/$IDOKLAD_SECRET_VAR) nejsou v env – přeskakuji${C_RST}"
    note "⚠ iDoklad creds chybí v env"
    return 0
  fi
  local resp tok
  resp=$(curl -sS --max-time 10 -X POST "$IDOKLAD_TOKEN_URL" \
          -H 'Content-Type: application/x-www-form-urlencoded' \
          --data-urlencode 'grant_type=client_credentials' \
          --data-urlencode "client_id=$id" \
          --data-urlencode "client_secret=$sec" \
          --data-urlencode "scope=$IDOKLAD_SCOPE" 2>/dev/null || echo '')
  tok=$(printf '%s' "$resp" | grep -o '"access_token":"[^"]*"' | head -1)
  if [[ -n "$tok" ]]; then
    log "${C_GRN}✓ iDoklad token OK – creds žijou, fetch faktur projede${C_RST}"
    note "✓ iDoklad creds OK"
  else
    log "${C_RED}✗ iDoklad token NEzískán – creds/scope problém${C_RST}"
    note "✗ iDoklad creds NEfungují (zkontroluj $IDOKLAD_ID_VAR/$IDOKLAD_SECRET_VAR/scope)"
    act "iDoklad: obnov client_id/secret v $ENV_FILE"
  fi
}

# Načti endpointy z registry JSON (pokud existuje) a přidej je k ENDPOINTS.
load_registry(){
  [[ -f "$ELIAS_REGISTRY_FILE" ]] || return 0
  command -v python3 >/dev/null 2>&1 || { log "${C_YEL}! registry: python3 chybí, přeskakuji${C_RST}"; return 0; }
  local lines added=0
  lines=$(python3 - "$ELIAS_REGISTRY_FILE" <<'PY' 2>/dev/null || true
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
items = data.get("endpoints", data) if isinstance(data, dict) else data
for it in items or []:
    n = (it.get("name") or "").strip()
    u = (it.get("url") or "").strip()
    t = (it.get("type") or "local").strip()
    if n and u:
        print(f"{n}|{u}|{t}")
PY
)
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    local rname="${row%%|*}" dup=0 e
    for e in "${ENDPOINTS[@]}"; do [[ "${e%%|*}" == "$rname" ]] && { dup=1; break; }; done
    [[ "$dup" == "0" ]] && { ENDPOINTS+=("$row"); added=$((added+1)); }
  done <<<"$lines"
  [[ "$added" -gt 0 ]] && log "✓ registry: přidáno $added endpointů z $ELIAS_REGISTRY_FILE"
}

# Zapiš výpadek do Nexus notifikací (in-app), když je co hlásit.
notify_nexus(){
  [[ -z "$NEXUS_API_BASE" || -z "$NEXUS_API_KEY" ]] && return 0
  [[ -z "$ACTIONS" ]] && return 0
  local sev="warn"; [[ "$FAIL_LOCAL" -ne 0 ]] && sev="error"
  local host; host=$(hostname 2>/dev/null || echo node)
  local body; body="MCP heal @ $host"$'\n'"$ACTIONS"
  local code
  code=$(curl -sS -k -o /dev/null -w '%{http_code}' --max-time 10 \
    -X POST "${NEXUS_API_BASE%/}/api/v1/notifications" \
    -H "X-API-Key: $NEXUS_API_KEY" -H 'Content-Type: application/json' \
    --data "$(printf '{"title":%s,"body":%s,"severity":%s,"related_type":"general"}' \
              "\"🩺 Elias MCP heal: zásah ($host)\"" \
              "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$body" 2>/dev/null || echo "\"$host\"")" \
              "\"$sev\"")" 2>/dev/null || echo 000)
  if [[ "$code" =~ ^2 ]]; then log "✓ Nexus notifikace zapsána (HTTP $code)"
  else log "${C_YEL}! Nexus notifikace selhala (HTTP $code)${C_RST}"; fi
}

notify_telegram(){
  local tok="${TELEGRAM_BOT_TOKEN:-}"
  [[ -z "$tok" || -z "$TELEGRAM_CHAT_ID" ]] && return 0
  local host; host=$(hostname 2>/dev/null || echo node)
  local msg="🩺 Elias MCP heal @ $host $(date '+%F %T')"$'\n\n'"$SUMMARY"
  [[ -n "$ACTIONS" ]] && msg+=$'\n👉 Akce:\n'"$ACTIONS"
  curl -sS --max-time 10 "https://api.telegram.org/bot$tok/sendMessage" \
    --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
    --data-urlencode "text=$msg" >/dev/null 2>&1 || true
}

install_timer(){
  if command -v systemctl >/dev/null 2>&1; then
    local svc=/etc/systemd/system/elias-mcp-heal.service
    local tmr=/etc/systemd/system/elias-mcp-heal.timer
    $SUDO tee "$svc" >/dev/null <<EOF
[Unit]
Description=Elias MCP heal
[Service]
Type=oneshot
ExecStart=$SCRIPT_PATH
EOF
    $SUDO tee "$tmr" >/dev/null <<EOF
[Unit]
Description=Elias MCP heal every ${INTERVAL_MIN}min
[Timer]
OnBootSec=2min
OnUnitActiveSec=${INTERVAL_MIN}min
Persistent=true
[Install]
WantedBy=timers.target
EOF
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable --now elias-mcp-heal.timer
    log "${C_GRN}✓ systemd timer aktivní (každých ${INTERVAL_MIN} min)${C_RST}"
    $SUDO systemctl status elias-mcp-heal.timer --no-pager 2>/dev/null | head -4 || true
  elif command -v launchctl >/dev/null 2>&1; then
    local plist="$HOME/Library/LaunchAgents/cz.investimenti.elias-mcp-heal.plist"
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>cz.investimenti.elias-mcp-heal</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$SCRIPT_PATH</string></array>
  <key>StartInterval</key><integer>$((INTERVAL_MIN*60))</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG_FILE</string>
  <key>StandardErrorPath</key><string>$LOG_FILE</string>
</dict></plist>
EOF
    launchctl unload "$plist" 2>/dev/null || true
    launchctl load "$plist" 2>/dev/null && log "${C_GRN}✓ LaunchAgent aktivní (každých ${INTERVAL_MIN} min)${C_RST}"
  else
    log "${C_RED}✗ Ani systemd ani launchctl – přidej cron ručně: */${INTERVAL_MIN} * * * * $SCRIPT_PATH${C_RST}"
  fi
}

usage(){
  sed -n '3,16p' "$SCRIPT_PATH" | sed 's/^# \{0,1\}//'
}

main(){
  local mode="${1:-heal}"
  case "$mode" in
    -h|--help|help) usage; exit 0 ;;
  esac
  log "════════ Elias MCP heal | host=$(hostname 2>/dev/null) | mode=$mode ════════"
  load_env
  load_registry
  case "$mode" in
    --install-timer) install_timer; exit 0 ;;
    --report) probe_all; check_idoklad ;;
    heal|"") probe_all
       if [[ -n "$ACTIONS" ]]; then heal_local; fi
       check_idoklad
       notify_nexus
       notify_telegram ;;
    *) log "${C_RED}✗ Neznámý argument: $mode${C_RST}"; usage; exit 2 ;;
  esac
  log "── SHRNUTÍ ───────────────────────────────────────"
  printf '%s' "$SUMMARY" | tee -a "$LOG_FILE"
  [[ -n "$ACTIONS" ]] && { log "👉 AKCE:"; printf '%s' "$ACTIONS" | tee -a "$LOG_FILE"; }
  if [[ "$FAIL_LOCAL" -ne 0 ]]; then
    log "${C_RED}⚠ Lokální služba pořád DOWN – zásah nutný${C_RST}"; exit 1
  fi
  log "${C_GRN}✓ Lokální MCP/bridge OK${C_RST}"; exit 0
}
main "$@"
