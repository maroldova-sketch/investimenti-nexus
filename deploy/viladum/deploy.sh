#!/usr/bin/env bash
set -euo pipefail
BUNDLE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)

usage() {
  cat <<'HELP'
Deploy only public/ to a dedicated Viladum release directory.

deploy.sh [--ssh fortress] [--sudo] --root /host/dedicated/viladum \
  --mode files|host|container [--nginx-conf /host/included/viladum.conf] \
  [--nginx-root /container/mapped/viladum] [--container investimenti-root] \
  [--listen 80|443|127.0.0.1:8080] [--tls-cert /existing/cert] \
  [--tls-key /existing/key] [--dry-run]

All paths and the origin listener must come from actual server inspection.
files: stage content only; existing vhost must already point to ROOT/current.
host: run host nginx -t, then nginx -s reload.
container: run docker exec CONTAINER nginx -t, then nginx -s reload.
For a container, mount the ENTIRE dedicated root, not just its current symlink.
--ssh transfers directly over SSH; no temporary file-hosting service is used.
--sudo uses non-interactive sudo on the SSH target.
HELP
}

die() { printf '%s\n' "$*" >&2; exit 1; }
SSH_HOST=; USE_SUDO=0; FORWARD=()
while (($#)); do
  case "$1" in
    --ssh) (($# >= 2)) || die 'Missing SSH host'; SSH_HOST=$2; shift 2 ;;
    --sudo) USE_SUDO=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) FORWARD+=("$1"); shift ;;
  esac
done
if [[ -n "$SSH_HOST" ]]; then
  [[ "$SSH_HOST" =~ ^[A-Za-z0-9_][A-Za-z0-9_.@-]*$ ]] || die 'Invalid SSH alias'
  command -v ssh >/dev/null; command -v tar >/dev/null
  REMOTE_DIR=$(ssh -o BatchMode=yes "$SSH_HOST" 'umask 077; mktemp -d /tmp/viladum.XXXXXXXX')
  [[ "$REMOTE_DIR" =~ ^/tmp/viladum\.[A-Za-z0-9]+$ ]] || die 'Unexpected SSH staging path'
  tar --exclude=.venv --exclude=__pycache__ --exclude=.git --exclude=.DS_Store \
    -C "$BUNDLE" -cf - . | ssh -o BatchMode=yes "$SSH_HOST" "tar -xf - -C '$REMOTE_DIR'"
  REMOTE_COMMAND=()
  ((USE_SUDO == 0)) || REMOTE_COMMAND+=(sudo -n)
  REMOTE_COMMAND+=(bash "$REMOTE_DIR/deploy.sh" "${FORWARD[@]}")
  printf -v REMOTE_TEXT '%q ' "${REMOTE_COMMAND[@]}"
  ssh -o BatchMode=yes "$SSH_HOST" "$REMOTE_TEXT"
  printf 'SSH staging retained at %s for diagnosis. Run verification on the Mac.\n' "$REMOTE_DIR"
  exit 0
fi
((USE_SUDO == 0)) || die '--sudo is only valid together with --ssh'
set -- "${FORWARD[@]}"
PROJECT_ROOT=; MODE=; NGINX_CONF=; NGINX_ROOT=; CONTAINER=; LISTEN=80
TLS_CERT=; TLS_KEY=; DRY_RUN=0
while (($#)); do
  case "$1" in
    --root|--mode|--nginx-conf|--nginx-root|--container|--listen|--tls-cert|--tls-key)
      (($# >= 2)) || die "Missing value for $1"
      case "$1" in
        --root) PROJECT_ROOT=$2 ;; --mode) MODE=$2 ;; --nginx-conf) NGINX_CONF=$2 ;;
        --nginx-root) NGINX_ROOT=$2 ;; --container) CONTAINER=$2 ;;
        --listen) LISTEN=$2 ;; --tls-cert) TLS_CERT=$2 ;; --tls-key) TLS_KEY=$2 ;;
      esac
      shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) die "Unknown argument: $1" ;;
  esac
done
[[ -n "$PROJECT_ROOT" && -n "$MODE" ]] || { usage; die '--root and --mode are required'; }
[[ "$MODE" == files || "$MODE" == host || "$MODE" == container ]] || die 'Invalid mode'
safe_path() { [[ "$1" =~ ^/[A-Za-z0-9_./-]+$ && "$1" != *'/../'* && "$1" != */.. ]]; }
safe_path "$PROJECT_ROOT" || die 'Use an absolute, simple dedicated root path'
[[ "$PROJECT_ROOT" != / && "$PROJECT_ROOT" != /var/www && "$PROJECT_ROOT" != /srv && "$PROJECT_ROOT" != /etc ]] || die 'Root must be dedicated to this project'
[[ "$PROJECT_ROOT" == *viladum* ]] || die 'Dedicated root path must contain viladum'
[[ -z "$NGINX_ROOT" ]] && NGINX_ROOT=$PROJECT_ROOT
safe_path "$NGINX_ROOT" || die 'Invalid mapped nginx root'
[[ "$LISTEN" =~ ^([0-9]{1,5}|[0-9.]+:[0-9]{1,5})$ ]] || die 'Use the observed numeric origin listener'
[[ -z "$TLS_CERT" || -n "$TLS_KEY" ]] || die 'TLS requires both existing certificate and key paths'
[[ -z "$TLS_KEY" || -n "$TLS_CERT" ]] || die 'TLS requires both existing certificate and key paths'
if [[ -n "$TLS_CERT" ]]; then safe_path "$TLS_CERT" && safe_path "$TLS_KEY" || die 'Invalid TLS paths'; fi
if [[ "$MODE" != files ]]; then
  safe_path "$NGINX_CONF" || die '--nginx-conf must be the observed included host config path'
  [[ "$NGINX_CONF" == *viladum* ]] || die 'Only the dedicated Viladum vhost file may be changed'
  [[ -d "$(dirname "$NGINX_CONF")" ]] || die 'Config directory does not exist'
  if [[ "$LISTEN" == 443 || "$LISTEN" == *:443 ]]; then
    [[ -n "$TLS_CERT" ]] || die 'Origin port 443 requires the existing TLS paths'
  fi
fi
if [[ "$MODE" == container ]]; then
  [[ "$CONTAINER" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || die 'Specify the observed nginx container'
  command -v docker >/dev/null
  docker inspect "$CONTAINER" >/dev/null
fi
if [[ "$MODE" == host ]]; then command -v nginx >/dev/null; fi
command -v python3 >/dev/null
python3 "$BUNDLE/scripts/verify.py" --bundle
nginx_command() {
  if [[ "$MODE" == container ]]; then docker exec "$CONTAINER" nginx "$@"; else nginx "$@"; fi
}
if [[ "$MODE" != files ]]; then nginx_command -t; fi
if ((DRY_RUN)); then
  printf 'Validated bundle. No files changed.\nmode=%s\nhost_root=%s\nnginx_root=%s\nconfig=%s\nlisten=%s\n' "$MODE" "$PROJECT_ROOT" "$NGINX_ROOT" "$NGINX_CONF" "$LISTEN"
  exit 0
fi
[[ $(uname -s) == Linux ]] || die 'Run deployment on fortress Linux, or use --ssh fortress'
command -v flock >/dev/null || die 'Linux flock is required'
if [[ -e "$PROJECT_ROOT" && ! -f "$PROJECT_ROOT/.viladum-managed" ]]; then
  [[ -d "$PROJECT_ROOT" && ! -L "$PROJECT_ROOT" ]] || die 'Dedicated root must be an ordinary directory'
  [[ -z "$(find "$PROJECT_ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]] || die 'Existing nonempty root is unmanaged; choose an isolated project directory'
fi
mkdir -p "$PROJECT_ROOT"
exec 9>"$PROJECT_ROOT/.deploy.lock"
flock -n 9 || die 'Another Viladum deployment is running'
touch "$PROJECT_ROOT/.viladum-managed"
mkdir -p "$PROJECT_ROOT/releases" "$PROJECT_ROOT/backups"
chmod 755 "$PROJECT_ROOT" "$PROJECT_ROOT/releases"
NEEDED=$(python3 - "$BUNDLE/public" <<'PY'
from pathlib import Path
import sys
print(sum(p.stat().st_size for p in Path(sys.argv[1]).rglob('*') if p.is_file()) * 3 + 50_000_000)
PY
)
AVAILABLE=$(df -Pk "$PROJECT_ROOT" | awk 'NR==2 {print $4 * 1024}')
python3 - "$AVAILABLE" "$NEEDED" <<'PY'
import sys
if float(sys.argv[1]) < int(sys.argv[2]): raise SystemExit('Insufficient free space for this deployment')
PY
RELEASE_ID=$(date -u +%Y%m%dT%H%M%SZ)-$$
RELEASE="$PROJECT_ROOT/releases/$RELEASE_ID"
mkdir "$RELEASE"
cp -R "$BUNDLE/public/." "$RELEASE/"
find "$RELEASE" -type d -exec chmod 755 {} +
find "$RELEASE" -type f -exec chmod 644 {} +
python3 "$BUNDLE/scripts/verify.py" --release "$RELEASE"
OLD_LINK=
if [[ -L "$PROJECT_ROOT/current" ]]; then
  OLD_LINK=$(readlink "$PROJECT_ROOT/current")
  [[ "$OLD_LINK" =~ ^releases/[A-Za-z0-9_.-]+$ ]] || die 'Unexpected current symlink; inspect manually'
elif [[ -e "$PROJECT_ROOT/current" ]]; then die 'current exists but is not a managed symlink'; fi
BACKUP="$PROJECT_ROOT/backups/$RELEASE_ID"
mkdir "$BACKUP"
printf '%s\n' "$OLD_LINK" > "$BACKUP/previous-current.txt"
printf '%s\n' "$MODE" > "$BACKUP/mode.txt"
printf '%s\n' "$NGINX_CONF" > "$BACKUP/nginx-conf-path.txt"
printf '%s\n' "$CONTAINER" > "$BACKUP/container.txt"
CONFIG_EXISTED=0; CONFIG_TOUCHED=0; LINK_TOUCHED=0; COMPLETED=0
if [[ "$MODE" != files && -f "$NGINX_CONF" ]]; then
  cp -L -p "$NGINX_CONF" "$BACKUP/previous-nginx.conf"
  CONFIG_EXISTED=1
fi
recover() {
  local result=$?
  if ((COMPLETED == 0)); then
    set +e
    if ((CONFIG_TOUCHED)); then
      if ((CONFIG_EXISTED)); then cp -p "$BACKUP/previous-nginx.conf" "$NGINX_CONF"; else rm -f "$NGINX_CONF"; fi
    fi
    if ((LINK_TOUCHED)); then
      if [[ -n "$OLD_LINK" ]]; then
        ln -s "$OLD_LINK" "$PROJECT_ROOT/.restore-$$"
        mv -Tf "$PROJECT_ROOT/.restore-$$" "$PROJECT_ROOT/current"
      else rm -f "$PROJECT_ROOT/current"; fi
    fi
    if [[ "$MODE" != files ]]; then nginx_command -t && nginx_command -s reload; fi
    printf 'Deployment failed; previous vhost and current release restored. Backup: %s\n' "$BACKUP" >&2
  fi
  exit "$result"
}
trap recover EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [[ "$MODE" != files ]]; then
  python3 - "$BUNDLE/nginx/viladum.conf.tpl" "$BACKUP/new-nginx.conf" "$NGINX_ROOT" "$LISTEN" "$TLS_CERT" "$TLS_KEY" <<'PY'
from pathlib import Path
import sys
src,out,root,listen,cert,key=sys.argv[1:]
tls=f'ssl_certificate {cert};\n    ssl_certificate_key {key};' if cert else ''
text=Path(src).read_text().replace('@LISTEN@',listen + (' ssl' if cert else '')).replace('@TLS@',tls).replace('@NGINX_ROOT@',root)
Path(out).write_text(text)
PY
  CONFIG_TOUCHED=1
  cp "$BACKUP/new-nginx.conf" "$NGINX_CONF"
fi
ln -s "releases/$RELEASE_ID" "$PROJECT_ROOT/.next-$$"
LINK_TOUCHED=1
mv -Tf "$PROJECT_ROOT/.next-$$" "$PROJECT_ROOT/current"
if [[ "$MODE" != files ]]; then
  CHECK_OUTPUT=$(nginx_command -t 2>&1) || { printf '%s\n' "$CHECK_OUTPUT" >&2; exit 1; }
  printf '%s\n' "$CHECK_OUTPUT"
  if [[ "$CHECK_OUTPUT" == *'conflicting server name "viladum.investimenti.cz"'* ]]; then die 'Duplicate Viladum vhost; restore and inspect the existing exact host'; fi
  nginx_command -s reload
fi
COMPLETED=1
trap - EXIT INT TERM
printf 'Content installed: %s\nRollback state: %s\n' "$RELEASE" "$BACKUP"
printf 'Verify publicly on the Mac: ./verify.sh --live\n'
