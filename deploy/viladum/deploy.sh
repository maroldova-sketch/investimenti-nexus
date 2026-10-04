#!/usr/bin/env bash
# Nasazení viladum.investimenti.cz na fortress.
# Spouštět z Macu (má SSH na fortress). Idempotentní – lze pouštět opakovaně.
#
#   ./deploy.sh                 # plné nasazení (web + brožura + kontejner + ověření)
#   BROZURA=/cesta/k/brozura.pdf ./deploy.sh
#   ./deploy.sh --dry-run       # jen ukáže, co by udělal
#
# Konvence fortress (viz audits/APP_REGISTRY.yaml): každý statický web = nginx:alpine
# kontejner s read-only bind mountem z /home/ubuntu/sites/<name>, port 81xx na 127.0.0.1,
# Cloudflare tunnel směruje hostname na ten port. Catch-all *.investimenti.cz jde dnes
# na alias-redirects (:8120) – proto web vrací 404, dokud není ingress pravidlo.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORTRESS_HOST="${FORTRESS_HOST:-fortress}"          # SSH alias na Macu
REMOTE_USER="${REMOTE_USER:-ubuntu}"
SITE_NAME="viladum-web"
REMOTE_DIR="/home/${REMOTE_USER}/sites/${SITE_NAME}"
PORT="${PORT:-8130}"
HOSTNAME_PUBLIC="viladum.investimenti.cz"
IMAGE="nginx:alpine"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

log(){ printf '\033[1;34m[viladum]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[viladum] VAROVÁNÍ:\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31m[viladum] CHYBA:\033[0m %s\n' "$*" >&2; exit 1; }
run(){ if [[ $DRY -eq 1 ]]; then echo "+ $*"; else "$@"; fi; }
rssh(){ if [[ $DRY -eq 1 ]]; then echo "+ ssh ${FORTRESS_HOST} $*"; else ssh -o BatchMode=yes "${FORTRESS_HOST}" "$@"; fi; }

# ---------- 0. předpoklady ----------
command -v rsync >/dev/null || die "chybí rsync"
ssh -o BatchMode=yes -o ConnectTimeout=10 "${FORTRESS_HOST}" true 2>/dev/null \
  || die "SSH na '${FORTRESS_HOST}' nefunguje (zkontroluj ~/.ssh/config na Macu)"
log "SSH na ${FORTRESS_HOST} OK"

# ---------- 1. brožura ----------
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "${HERE}/site/." "${STAGE}/"

find_brozura(){
  if [[ -n "${BROZURA:-}" && -f "${BROZURA}" ]]; then echo "${BROZURA}"; return; fi
  local c
  for c in "${HERE}/brozura.pdf" "${HERE}/site/brozura.pdf" \
           "$HOME/Downloads/Viladům v zahradách brožura.pdf" \
           "$HOME/Downloads/brozura.pdf"; do
    [[ -f "$c" ]] && { echo "$c"; return; }
  done
  # Google Drive for Desktop / Spotlight
  local gd
  for gd in "$HOME"/Library/CloudStorage/GoogleDrive-*/; do
    [[ -d "$gd" ]] || continue
    c="$(find "$gd" -maxdepth 6 -iname 'Viladům v zahradách brožura*.pdf' ! -iname 'ROZPOČET*' 2>/dev/null | head -1 || true)"
    [[ -n "$c" ]] && { echo "$c"; return; }
  done
  if command -v mdfind >/dev/null; then
    c="$(mdfind -name 'Viladům v zahradách brožura' 2>/dev/null | grep -i '\.pdf$' | grep -vi 'ROZPO' | head -1 || true)"
    [[ -n "$c" ]] && { echo "$c"; return; }
  fi
  echo ""
}

BROZURA_SRC="$(find_brozura)"
if [[ -z "$BROZURA_SRC" ]]; then
  warn "brožura nenalezena. Web se nasadí bez /brozura.pdf (odkaz bude 404)."
  warn "Zdroj: Google Drive 'Viladům v zahradách brožura.pdf' (58 MB). Stáhni ji a spusť: BROZURA=/cesta/soubor.pdf $0"
else
  log "brožura: ${BROZURA_SRC}"
  case "$(basename "$BROZURA_SRC")" in
    *ROZPO*|*rozpo*) die "Tohle je rozpočtová verze brožury (interní). Nepublikovat." ;;
  esac
  cp "$BROZURA_SRC" "${STAGE}/brozura-tisk.pdf"
  # volitelná web komprese (ghostscript), originál zůstane jako brozura-tisk.pdf
  if command -v gs >/dev/null; then
    log "komprimuji PDF pro web (gs /ebook)…"
    if gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook -dCompatibilityLevel=1.5 \
         -sOutputFile="${STAGE}/brozura.pdf" "${STAGE}/brozura-tisk.pdf" 2>/dev/null \
       && [[ -s "${STAGE}/brozura.pdf" ]]; then
      log "web PDF: $(du -h "${STAGE}/brozura.pdf" | cut -f1) (originál $(du -h "${STAGE}/brozura-tisk.pdf" | cut -f1))"
    else
      warn "komprese selhala, použiji originál"; cp "${STAGE}/brozura-tisk.pdf" "${STAGE}/brozura.pdf"
    fi
  else
    cp "${STAGE}/brozura-tisk.pdf" "${STAGE}/brozura.pdf"
  fi
fi
printf 'User-agent: *\nAllow: /\nSitemap: https://%s/sitemap.xml\n' "$HOSTNAME_PUBLIC" > "${STAGE}/robots.txt"
printf '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://%s/</loc></url></urlset>\n' "$HOSTNAME_PUBLIC" > "${STAGE}/sitemap.xml"

# ---------- 2. upload na fortress ----------
log "upload do ${FORTRESS_HOST}:${REMOTE_DIR}"
rssh "mkdir -p '${REMOTE_DIR}/html' '${REMOTE_DIR}/nginx' && \
      if [ -d '${REMOTE_DIR}/html' ] && [ -n \"\$(ls -A '${REMOTE_DIR}/html' 2>/dev/null)\" ]; then \
        tar -C '${REMOTE_DIR}' -czf \"${REMOTE_DIR}/backup-\$(date +%Y%m%d-%H%M%S).tgz\" html nginx; fi"
run rsync -az --delete --exclude 'backup-*.tgz' "${STAGE}/" "${FORTRESS_HOST}:${REMOTE_DIR}/html/"
run rsync -az "${HERE}/nginx/default.conf" "${FORTRESS_HOST}:${REMOTE_DIR}/nginx/default.conf"

# ---------- 3. kontejner ----------
log "kontejner ${SITE_NAME} na 127.0.0.1:${PORT}"
rssh "set -e
  if docker ps -a --format '{{.Names}}' | grep -qx '${SITE_NAME}'; then
    docker rm -f '${SITE_NAME}' >/dev/null
  fi
  if ss -ltn 2>/dev/null | awk '{print \$4}' | grep -q ':${PORT}\$'; then
    echo 'port ${PORT} je obsazený jiným procesem' >&2; exit 2
  fi
  docker run -d --name '${SITE_NAME}' --restart unless-stopped \
    -p 127.0.0.1:${PORT}:80 \
    -v '${REMOTE_DIR}/html:/usr/share/nginx/html:ro' \
    -v '${REMOTE_DIR}/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro' \
    '${IMAGE}' >/dev/null
  sleep 1
  docker exec '${SITE_NAME}' nginx -t
  curl -fsS -o /dev/null -w 'lokálně: HTTP %{http_code}\n' -H 'Host: ${HOSTNAME_PUBLIC}' http://127.0.0.1:${PORT}/"

# ---------- 4. ingress v Cloudflare tunelu ----------
# Varianta A: lokálně spravovaný tunel (/etc/cloudflared/config.yml s 'ingress:')
# Varianta B: tunel spravovaný z dashboardu (token) -> pravidlo přes Cloudflare API / dashboard.
log "ingress pro ${HOSTNAME_PUBLIC} -> http://127.0.0.1:${PORT}"
rssh "set -e
  CFG=''
  for f in /etc/cloudflared/config.yml /etc/cloudflared/config.yaml /home/${REMOTE_USER}/.cloudflared/config.yml; do
    [ -f \"\$f\" ] && grep -q '^ingress:' \"\$f\" && CFG=\"\$f\" && break
  done
  if [ -z \"\$CFG\" ]; then
    echo 'INGRESS: lokální config s ingress nenalezen -> tunel je spravovaný z Cloudflare (token).'
    echo 'INGRESS: přidej public hostname ${HOSTNAME_PUBLIC} -> http://127.0.0.1:${PORT} (Zero Trust > Networks > Tunnels),'
    echo 'INGRESS: nebo přes API (viz README.md, sekce Ingress). Pravidlo musí být PŘED catch-all *.investimenti.cz.'
    exit 0
  fi
  if grep -q 'hostname: *${HOSTNAME_PUBLIC}' \"\$CFG\"; then
    echo \"INGRESS: pravidlo už existuje v \$CFG\"; exit 0
  fi
  sudo cp \"\$CFG\" \"\$CFG.bak-\$(date +%Y%m%d-%H%M%S)\"
  # vložit před první catch-all položku (- service: ... bez hostname) nebo před wildcard *.investimenti.cz
  sudo python3 - \"\$CFG\" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p).read().splitlines(keepends=True)
out=[]; done=False
for i,l in enumerate(s):
    if not done and re.match(r'^\s*-\s*(service:|hostname:\s*\*\.investimenti\.cz)', l):
        ind=re.match(r'^(\s*)-', l).group(1)
        out.append(f'{ind}- hostname: ${HOSTNAME_PUBLIC}\n{ind}  service: http://127.0.0.1:${PORT}\n')
        done=True
    out.append(l)
if not done: sys.exit('nenašel jsem místo pro vložení pravidla')
open(p,'w').write(''.join(out))
PY
  sudo cloudflared tunnel ingress validate --config \"\$CFG\" || { echo 'validate selhal, vracím zálohu'; sudo cp \"\$CFG.bak-\"* \"\$CFG\"; exit 3; }
  sudo systemctl restart cloudflared 2>/dev/null || sudo systemctl restart 'cloudflared*' || true
  echo \"INGRESS: přidáno do \$CFG a cloudflared restartován\""

# ---------- 5. ověření zvenku ----------
log "ověření https://${HOSTNAME_PUBLIC}/"
sleep 3
code="$(curl -sS -o /dev/null -w '%{http_code}' "https://${HOSTNAME_PUBLIC}/" || true)"
echo "GET /            -> HTTP ${code}"
if [[ "$code" == "200" ]]; then
  curl -sS "https://${HOSTNAME_PUBLIC}/" | grep -q 'Viladům v' && echo "obsah: OK (stránka Viladům)"
  pdf="$(curl -sS -o /dev/null -w '%{http_code} %{content_type} %{size_download}' -r 0-1023 "https://${HOSTNAME_PUBLIC}/brozura.pdf" || true)"
  echo "GET /brozura.pdf -> ${pdf}"
  echo "QR: /qr.png kóduje https://${HOSTNAME_PUBLIC}/ (ověř skenem telefonem)"
else
  warn "web zvenku ještě nevrací 200 – obvykle chybí ingress pravidlo v tunelu (viz výstup INGRESS výše)."
fi
log "hotovo"
