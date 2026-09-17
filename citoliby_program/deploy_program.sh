#!/usr/bin/env bash
# deploy_program.sh — modul PROGRAM do Cítoliby dashboardu (Mac 192.168.1.43)
# Idempotentní. Nic nemaže, před každým přepisem dělá .bak.<timestamp>.
#
#   bash deploy_program.sh            # plné nasazení: soubory + backend + restart + testy + git commit
#   SKIP_RESTART=1 SKIP_GIT=1 bash deploy_program.sh   # jen soubory (např. lokální zkouška)
#   CASTELLO=... BACKEND=... PORT=...  # přepsání cest
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CASTELLO="${CASTELLO:-$HOME/castello-citoliby}"
BACKEND="${BACKEND:-$HOME/andrew_core/sites/citoliby-d/backend.py}"
PORT="${PORT:-8017}"
SERVICE="${SERVICE:-cz.investimenti.citoliby.d}"
TS="$(date +%Y%m%d_%H%M%S)"
MASTER="$CASTELLO/internal/index_master.html"
DATA="$CASTELLO/dashboard/data/program.json"
GIT_EMAIL="${GIT_EMAIL:-elias.marold@investimenti.cz}"
GIT_NAME="${GIT_NAME:-Elias Marold}"

log() { printf '\n== %s\n' "$*"; }
need() { [ -e "$1" ] || { echo "CHYBÍ: $1" >&2; exit 2; }; }
need "$HERE/program.json"; need "$HERE/program_tab_section.html"; need "$HERE/program_tab.js"
need "$MASTER"; need "$BACKEND"
command -v python3 >/dev/null || { echo "CHYBÍ python3" >&2; exit 2; }

log "KROK 2: program.json -> $DATA"
mkdir -p "$(dirname "$DATA")"
python3 -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); assert len(d['katalog'])==6 and len(d['kalendar'])>=20 and sum(s['mist'] for s in d['cenik']['sektory'])==902; print('program.json validní: katalog',len(d['katalog']),'kalendář',len(d['kalendar']))" "$HERE/program.json"
if [ -e "$DATA" ] && ! cmp -s "$HERE/program.json" "$DATA"; then cp -p "$DATA" "$DATA.bak.$TS"; echo "záloha: $DATA.bak.$TS"; fi
cp "$HERE/program.json" "$DATA"

log "KROK 3: tab PROGRAM -> $MASTER"
if grep -q 'data-tab="program"' "$MASTER"; then
  echo "index_master.html už tab program má, přeskakuji (záloha se nedělá)"
else
  cp -p "$MASTER" "$MASTER.bak.$TS"; echo "záloha: $MASTER.bak.$TS"
  MASTER="$MASTER" SEC="$HERE/program_tab_section.html" JS="$HERE/program_tab.js" python3 - <<'PY'
import os, pathlib
p = pathlib.Path(os.environ['MASTER']); h = p.read_text(encoding='utf-8')
sec = pathlib.Path(os.environ['SEC']).read_text(encoding='utf-8')
js = pathlib.Path(os.environ['JS']).read_text(encoding='utf-8')
assert 'id="tab-program"' in sec and js.startswith('/* === TAB PROGRAM')
nav = '<div class="castello-tab" data-tab="kultura">🎭 Kultura</div>'
assert h.count(nav) == 1, 'nav anchor (tab kultura) nenalezen nebo není unikátní'
i = h.index(nav) + len(nav)
h = h[:i] + '\n    <div class="castello-tab" data-tab="program">🗓️ Program</div>' + h[i:]
anchor = '<!-- TAB: ARCHITEKTURA -->'
assert h.count(anchor) == 1, 'section anchor (TAB: ARCHITEKTURA) nenalezen nebo není unikátní'
j = h.rindex('\n', 0, h.index(anchor)) + 1
h = h[:j] + sec + h[j:]
scr = '<script>\n' + js + '</script>\n'
if '</script>' in h:
    k = h.rindex('</script>') + len('</script>'); h = h[:k] + '\n' + scr + h[k:]
else:
    assert '</body>' in h; h = h.replace('</body>', scr + '</body>')
p.write_text(h, encoding='utf-8')
print('index_master.html: tab', h.count('data-tab="program"'), 'sekce', h.count('id="tab-program"'), 'script', h.count('TAB PROGRAM: čte'), 'velikost', len(h.encode()))
PY
fi

log "KROK 4.2: backend routy -> $BACKEND"
if grep -q '=== PROGRAM (2026-09-16)' "$BACKEND"; then
  echo "backend.py už routy má, přeskakuji"
else
  cp -p "$BACKEND" "$BACKEND.bak.$TS"; echo "záloha: $BACKEND.bak.$TS"
  BACKEND="$BACKEND" BLOCK="$HERE/backend_program_routes.py" python3 - <<'PY'
import os, pathlib, ast
p = pathlib.Path(os.environ['BACKEND']); s = p.read_text(encoding='utf-8')
block = pathlib.Path(os.environ['BLOCK']).read_text(encoding='utf-8')
block = '\n'.join(l for l in block.splitlines() if not l.startswith('# Vkládá se') and not l.startswith('# (deploy_program.sh')) + '\n\n\n'
anchor = '@app.get("/{path:path}")\n'
assert s.count(anchor) == 1, 'catch-all anchor není unikátní'
for name in ('strip_founders', 'inject_banner', 'FileResponse', 'HTMLResponse', 'Response', 'Request'):
    assert name in s, f'v backend.py chybí {name}'
s = s.replace(anchor, block + anchor)
ast.parse(s)
p.write_text(s, encoding='utf-8')
lines = s.splitlines()
print('backend.py: blok PROGRAM na řádku', next(i+1 for i,l in enumerate(lines) if '=== PROGRAM (2026-09-16)' in l), ', catch-all teď na řádku', next(i+1 for i,l in enumerate(lines) if l.startswith('@app.get("/{path:path}")')))
PY
fi

if [ "${SKIP_RESTART:-0}" = "1" ]; then
  log "KROK 4.3/4.4 přeskočeno (SKIP_RESTART=1)"
else
  log "KROK 4.3: restart $SERVICE"
  launchctl kickstart -k "gui/$(id -u)/$SERVICE"
  sleep 2
  log "KROK 4.4: HTTP testy na localhost:$PORT"
  RC=0
  for path in /master /dashboard/data/program.json /api/program /health; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT$path" || echo 000)
    printf '  %-32s %s\n' "$path" "$code"
    case "$path" in /master|/dashboard/data/program.json) [ "$code" = "200" ] || RC=1;; esac
  done
  [ $RC = 0 ] || { echo "HTTP test SELHAL (viz výše). Zálohy: *.bak.$TS" >&2; exit 3; }
fi

if [ "${SKIP_GIT:-0}" = "1" ]; then
  log "KROK 4.5 přeskočeno (SKIP_GIT=1)"
else
  log "KROK 4.5: git commit v $CASTELLO"
  cd "$CASTELLO"
  git add dashboard/data/program.json internal/index_master.html
  if git diff --cached --quiet; then echo "nic ke commitu"; else
    git -c user.name="$GIT_NAME" -c user.email="$GIT_EMAIL" commit -m "feat(dashboard): modul PROGRAM, program.json jako zdroj pravdy"
    git log -1 --format='%h %an <%ae> %s'
  fi
fi
log "HOTOVO ($TS)"
