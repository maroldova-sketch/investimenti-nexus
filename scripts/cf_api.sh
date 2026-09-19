#!/usr/bin/env bash
# cf_api.sh — úzký wrapper pro Cloudflare API v4 (runner na Macu)
# Použití: cf_api.sh METHOD /cesta [JSON_FILE]
#   např.  cf_api.sh GET /accounts
#          cf_api.sh POST /accounts/ID/access/apps body.json
# Pravidla:
#   - volá se VŽDY jen https://api.cloudflare.com/client/v4$PATH, jiný host zadat nejde
#   - METHOD jen GET|POST|PUT|PATCH|DELETE
#   - token CF_API_TOKEN si čte sám z ~/andrew/.env (jen parsuje, nespouští),
#     curl ho dostane hlavičkou přes stdin (-H @-), nikdy jako argument, nikdy se nevypíše
#   - tělo požadavku jen ze souboru JSON_FILE, odpověď API jde na stdout
#   - každé volání zapíše řádek (čas, METHOD, PATH, HTTP kód) do ~/andrew_core/logs/cf_api.log
set -euo pipefail
set +x

API_BASE="https://api.cloudflare.com/client/v4"
ENV_FILE="${HOME}/andrew/.env"
LOG_FILE="${HOME}/andrew_core/logs/cf_api.log"
TOKEN_VAR="CF_API_TOKEN"   # stejná proměnná, jakou používá runtime/rotation/cf_auth.py

die() { printf 'cf_api: %s\n' "$*" >&2; exit 2; }
usage() { die "použití: cf_api.sh METHOD /cesta [JSON_FILE]   (METHOD = GET|POST|PUT|PATCH|DELETE)"; }

[ "$#" -ge 2 ] && [ "$#" -le 3 ] || usage
METHOD="$1"
API_PATH="$2"
BODY_FILE="${3:-}"

case "$METHOD" in
  GET|POST|PUT|PATCH|DELETE) ;;
  *) die "METHOD musí být GET, POST, PUT, PATCH nebo DELETE (dostal jsem: $METHOD)" ;;
esac

# PATH: musí začínat lomítkem, jen bezpečné znaky, žádné '..', '//', mezery, '@', '\'
[[ "$API_PATH" == /* ]] || die "PATH musí začínat lomítkem"
[[ "$API_PATH" =~ ^/[A-Za-z0-9._~/?=\&%,:+-]*$ ]] || die "PATH obsahuje nepovolené znaky"
[[ "$API_PATH" == *..* ]] && die "PATH nesmí obsahovat '..'"
[[ "$API_PATH" == *//* ]] && die "PATH nesmí obsahovat '//'"

if [ -n "$BODY_FILE" ]; then
  [ "$METHOD" != "GET" ] || die "GET nemá tělo"
  [ -f "$BODY_FILE" ] && [ -r "$BODY_FILE" ] || die "JSON_FILE neexistuje nebo není čitelný: $BODY_FILE"
fi

# Token: parsuj .env bez source, vezmi jen řádek TOKEN_VAR=..., odstraň uvozovky
[ -r "$ENV_FILE" ] || die "nemohu číst $ENV_FILE"
TOKEN=""
while IFS= read -r line || [ -n "$line" ]; do
  line="${line#"${line%%[![:space:]]*}"}"       # ltrim
  case "$line" in
    "export $TOKEN_VAR="*) line="${line#export }" ;;
    "$TOKEN_VAR="*) ;;
    *) continue ;;
  esac
  val="${line#"$TOKEN_VAR"=}"
  val="${val%%[[:space:]]#*}"                     # trailing komentář
  val="${val%"${val##*[![:space:]]}"}"           # rtrim
  case "$val" in
    \"*\") val="${val#\"}"; val="${val%\"}" ;;
    \'*\') val="${val#\'}"; val="${val%\'}" ;;
  esac
  TOKEN="$val"
done < "$ENV_FILE"
[ -n "$TOKEN" ] || die "v $ENV_FILE není $TOKEN_VAR"
[[ "$TOKEN" =~ ^[A-Za-z0-9_-]{20,}$ ]] || die "$TOKEN_VAR má neočekávaný formát"

umask 077
RESP="$(mktemp -t cf_api.XXXXXX)"
trap 'rm -f "$RESP"' EXIT

CURL_ARGS=( -q -sS --proto =https --max-redirs 0 --max-time 60
            -X "$METHOD" -H @- -H "Content-Type: application/json"
            -o "$RESP" -w '%{http_code}' )
if [ -n "$BODY_FILE" ]; then
  CURL_ARGS+=( --data-binary @"$BODY_FILE" )
fi

# Hlavička jde do curl přes stdin (-H @-), token nikdy není v argv ani v ps
CODE="$(printf 'Authorization: Bearer %s\n' "$TOKEN" | curl "${CURL_ARGS[@]}" "${API_BASE}${API_PATH}")" || CODE="000"
unset TOKEN

mkdir -p "$(dirname "$LOG_FILE")"
printf '%s %s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$METHOD" "$API_PATH" "$CODE" >> "$LOG_FILE"

cat "$RESP"
[ -s "$RESP" ] && printf '\n'
case "$CODE" in
  2*) exit 0 ;;
  000) die "curl selhal (síť/TLS)" ;;
  *) exit 1 ;;
esac
