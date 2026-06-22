#!/usr/bin/env bash
# =====================================================================
# discover.sh — T1 Discovery. Read-only. Spouštěj na VPS (gateway) a/nebo Macu.
# Zmapuje Cloudflare DNS+tunely, Tailscale, docker, reverse proxy a dosah na
# Mac Bible/Registry. Zapíše docs/TOPOLOGY-now.md. NIC nemění.
#
#   CLOUDFLARE_API_TOKEN=... ./tools/gateway/discover.sh
#   (token se scope Zone:DNS:Read + Account:Cloudflare Tunnel:Read)
#
# Konfig z ~/andrew/.env nebo env: CF_ZONE (investimenti.cz), MAC_HOST (MagicDNS),
# BIBLE_PORT(8770), REGISTRY_PORT(8110).
# =====================================================================
set -uo pipefail

ENV_FILE="${ANDREW_ENV:-$HOME/andrew/.env}"
[[ -f "$ENV_FILE" ]] && { set -a; . "$ENV_FILE" 2>/dev/null || true; set +a; }
OUT="${TOPO_OUT:-docs/TOPOLOGY-now.md}"
CF_ZONE="${CF_ZONE:-investimenti.cz}"
MAC_HOST="${MAC_HOST:-}"
BIBLE_PORT="${BIBLE_PORT:-8770}"
REGISTRY_PORT="${REGISTRY_PORT:-8110}"
RPI_DEAD="${RPI_DEAD:-192.168.1.220}"
CFAPI="https://api.cloudflare.com/client/v4"

NL=$'\n'; REPORT=""
sec(){ REPORT+="${NL}## $1${NL}${NL}"; echo "── $1 ──"; }
line(){ REPORT+="$1${NL}"; echo "  $1"; }
have(){ command -v "$1" >/dev/null 2>&1; }
jqget(){ if have jq; then jq -r "$1" 2>/dev/null; else cat; fi; }

echo "════ discover @ $(hostname) $(date '+%F %T') ════"

# ── Cloudflare ────────────────────────────────────────────────────────
sec "Cloudflare — DNS & tunely ($CF_ZONE)"
if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  zid=$(curl -s "$CFAPI/zones?name=$CF_ZONE" -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jqget '.result[0].id')
  acc=$(curl -s "$CFAPI/zones?name=$CF_ZONE" -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jqget '.result[0].account.id')
  if [[ -n "$zid" && "$zid" != "null" ]]; then
    line "zone_id=$zid account_id=$acc"
    line ""
    line "DNS záznamy (name | type | content | proxied):"
    recs=$(curl -s "$CFAPI/zones/$zid/dns_records?per_page=200" -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN")
    if have jq; then
      while IFS=$'\t' read -r n t c p; do line "- $n | $t | $c | proxied=$p"; done \
        < <(echo "$recs" | jq -r '.result[] | [.name,.type,.content,(.proxied|tostring)] | @tsv')
      # mrtvý RPi
      dead=$(echo "$recs" | jq -r --arg ip "$RPI_DEAD" '.result[] | select(.content==$ip) | .name' )
      [[ -n "$dead" ]] && line "" && line "⚠ MÍŘÍ NA MRTVÝ RPi ($RPI_DEAD): $dead"
    else
      line "(nainstaluj jq pro parse; raw uložen do /tmp/cf_dns.json)"; echo "$recs" >/tmp/cf_dns.json
    fi
    line ""
    line "Named tunely:"
    if [[ -n "$acc" && "$acc" != "null" ]]; then
      curl -s "$CFAPI/accounts/$acc/cfd_tunnel?is_deleted=false" -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        | jqget '.result[] | "- \(.name) | \(.id) | conns=\(.connections|length)"' | while read -r l; do line "$l"; done
    fi
  else
    line "✗ zone $CF_ZONE nenalezena (token scope? Zone:Read)"
  fi
else
  line "✗ CLOUDFLARE_API_TOKEN chybí → CF discovery přeskočeno"
fi

# ── lokální docker / reverse proxy / cloudflared ─────────────────────
sec "Tento node ($(hostname)) — docker / proxy / cloudflared"
if have docker; then
  while read -r l; do line "- $l"; done < <(docker ps --format '{{.Names}} | {{.Image}} | {{.Ports}}' 2>/dev/null)
  prox=$(docker ps --format '{{.Image}}' 2>/dev/null | grep -Eio 'caddy|nginx|traefik' | sort -u | tr '\n' ' ')
  line "reverse proxy: ${prox:-žádný v dockeru}"
  cf=$(docker ps --format '{{.Image}} {{.Names}}' 2>/dev/null | grep -i cloudflared || true)
  line "cloudflared (docker): ${cf:-ne}"
else
  line "docker: není"
fi
if have cloudflared; then line "cloudflared (host): $(cloudflared --version 2>/dev/null | head -1)"; fi
pgrep -fl cloudflared >/dev/null 2>&1 && line "cloudflared proces: BĚŽÍ" || line "cloudflared proces: neběží"
for p in caddy nginx traefik; do pgrep -x "$p" >/dev/null 2>&1 && line "host proxy: $p BĚŽÍ"; done

# ── Tailscale ─────────────────────────────────────────────────────────
sec "Tailscale"
if have tailscale; then
  line "stav: $(tailscale status --json 2>/dev/null | jqget '.BackendState' )"
  line "self: $(tailscale status --json 2>/dev/null | jqget '.Self.DNSName')"
  if [[ -z "$MAC_HOST" ]] && have jq; then
    MAC_HOST=$(tailscale status --json 2>/dev/null | jq -r '.Peer[]?.DNSName' | grep -i mac | head -1 | sed 's/\.$//')
    [[ -n "$MAC_HOST" ]] && line "Mac MagicDNS (detekováno): $MAC_HOST"
  fi
  [[ -n "$MAC_HOST" ]] && line "Mac host: $MAC_HOST" || line "⚠ Mac MagicDNS jméno neurčeno → nastav MAC_HOST"
else
  line "✗ tailscale binárka chybí"
fi

# ── dosah na Mac Bible/Registry (přes Tailscale) ─────────────────────
sec "Dosah na Mac (Bible :$BIBLE_PORT, Registry :$REGISTRY_PORT)"
probe(){ local c; c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 6 "$1" 2>/dev/null); [[ "$c" =~ ^[0-9]{3}$ ]] || c=000; echo "$c"; }
if [[ -n "$MAC_HOST" ]]; then
  line "Bible    http://$MAC_HOST:$BIBLE_PORT/health → $(probe "http://$MAC_HOST:$BIBLE_PORT/health")"
  line "Registry http://$MAC_HOST:$REGISTRY_PORT/health → $(probe "http://$MAC_HOST:$REGISTRY_PORT/health")"
else
  line "(MAC_HOST neznámý — přeskočeno; nastav MAC_HOST a spusť znovu)"
fi

# ── Mac sleep/Tailscale (jen když běžíme na macOS) ───────────────────
if [[ "$(uname)" == "Darwin" ]]; then
  sec "Mac napájení / autostart"
  line "pmset sleep:"; while read -r l; do line "  $l"; done < <(pmset -g 2>/dev/null | grep -Ei 'sleep|displaysleep|disksleep' | head)
  have tailscale && line "tailscale: $(tailscale status --json 2>/dev/null | jqget '.BackendState')"
fi

# ── zápis ─────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$OUT")"
{
  echo "# T1 — TOPOLOGY (aktuální stav, discover.sh)"
  echo
  echo "_Generováno na \`$(hostname)\` $(date '+%F %T'). Read-only._"
  echo "$REPORT"
} > "$OUT"
echo "──── zapsáno → $OUT ────"
