#!/bin/bash
# citoliby-d: zabijačka checklist + state.json — deploy na Macu (2026-09-17)
# Spustit na Macu jako uživatel investimenti (LAN/SSH), jedním příkazem:
#   bash ~/deploy_zabijacka.sh
# Kroky: kontrola sha → zálohy → stažení stránky + nového backend.py (ověření sha256)
#        → odkaz v index_d.html → restart launchd agenta → ověření lokálně i zvenku → git commit.
# Bezpečné opakované spuštění (idempotentní). Při chybě rollback ze záloh .bak-2026-09-17.
set -uo pipefail

D=/Users/investimenti/andrew_core/sites/citoliby-d
IDX=/Users/investimenti/castello-citoliby/internal/index_d.html
ERRLOG=/Users/investimenti/andrew_core/logs/citoliby_d.err.log
LABEL=cz.investimenti.citoliby.d
BAK=bak-2026-09-17
PAGE_URL="https://dave.investimenti.cz/p/-nUT7NfwujV7HZFm_DCDjc9fcGcz4Hwx"
BACKEND_URL="https://dave.investimenti.cz/p/wg5A9xEJh1bmmeeD-uHONaB9p9AqWCly"
EXP_OLD=7f8dbdfeefaaaccb496250e1c288f58cded0def16912f01b0909a7de64f45b60
EXP_PAGE=dee5f5bce3ca5b83edd3825ca704bf748335ba31a8b6c2d64642d168f29a40a5
EXP_NEW=c1e3c1240c4952fbba84ddc2092858b796d8451dacf621744ddce008705eeadc
PUB=https://citoliby.investimenti.cz
LINK_LINE='    <a href="/zabijacka/" style="color:var(--gold);text-decoration:none;border-bottom:1px solid var(--gold);">Zabijačka, výbava (checklist)</a>'
ANCHOR='<a href="/navod" style="color:var(--gold);text-decoration:none;border-bottom:1px solid var(--gold);">NÁVOD</a>'

sha(){ shasum -a 256 "$1" | cut -d' ' -f1; }
step(){ printf '\n== %s\n' "$*"; }
die(){ echo "STOP: $*" >&2; exit 1; }
rollback(){
  echo "!! ROLLBACK: obnovuji backend.py a index_d.html ze záloh .$BAK a restartuji" >&2
  cp -p "$D/backend.py.$BAK" "$D/backend.py"
  cp -p "$IDX.$BAK" "$IDX"
  launchctl kickstart -k "gui/$(id -u)/$LABEL"
  exit 1
}

cd "$D" || die "chybí $D"

step "0 kontrola výchozího stavu"
CUR=$(sha backend.py); ALREADY=""
if grep -q ZABIJACKA_DIR backend.py; then
  echo "backend.py už obsahuje zabijacka routy (sha $CUR), výměna se přeskočí"; ALREADY=1
elif [ "$CUR" != "$EXP_OLD" ]; then
  die "backend.py má sha $CUR, očekávám $EXP_OLD (200 řádků). Neznámá verze, nic neměním."
else
  echo "backend.py sha OK ($CUR)"
fi

step "1 zálohy"
[ -e "backend.py.$BAK" ] || cp -p backend.py "backend.py.$BAK"
[ -e "$IDX.$BAK" ] || cp -p "$IDX" "$IDX.$BAK"
ls -l "backend.py.$BAK" "$IDX.$BAK"

step "2 stránka zabijacka/index.html"
mkdir -p zabijacka
curl -fsSL -o zabijacka/index.html.new "$PAGE_URL" || die "stažení stránky selhalo"
[ "$(sha zabijacka/index.html.new)" = "$EXP_PAGE" ] || { rm -f zabijacka/index.html.new; die "sha stránky nesedí"; }
[ "$(head -c 15 zabijacka/index.html.new)" = "<!doctype html>" ] || { rm -f zabijacka/index.html.new; die "stránka nezačíná <!doctype html>"; }
grep -q "Zabijačka na zámku" zabijacka/index.html.new || { rm -f zabijacka/index.html.new; die "stránka neobsahuje 'Zabijačka na zámku'"; }
mv zabijacka/index.html.new zabijacka/index.html
echo "index.html OK: $(wc -c < zabijacka/index.html) B, sha $EXP_PAGE"

step "3 nový backend.py"
if [ -z "$ALREADY" ]; then
  curl -fsSL -o backend.py.new "$BACKEND_URL" || die "stažení backend.py selhalo"
  [ "$(sha backend.py.new)" = "$EXP_NEW" ] || { rm -f backend.py.new; die "sha nového backend.py nesedí"; }
  python3 -m py_compile backend.py.new || { rm -f backend.py.new; die "backend.py.new se nezkompiluje"; }
  mv backend.py.new backend.py
  echo "backend.py vyměněn (sha $EXP_NEW, $(wc -l < backend.py) řádků)"
  diff "backend.py.$BAK" backend.py | grep -c '^[<>]' | sed 's/^/změněných řádků: /'
fi

step "4 odkaz v index_d.html"
if ! grep -q 'href="/zabijacka/"' "$IDX"; then
  IDX="$IDX" ANCHOR="$ANCHOR" LINK_LINE="$LINK_LINE" python3 - <<'PY' || rollback
import os
p=os.environ["IDX"]; a=os.environ["ANCHOR"]; l=os.environ["LINK_LINE"]
s=open(p,encoding="utf-8").read()
lines=s.split("\n")
hits=[i for i,x in enumerate(lines) if x.strip()==a]
assert len(hits)==1, f"anchor NÁVOD nalezen {len(hits)}x, čekám 1x"
lines.insert(hits[0]+1, l)
open(p,"w",encoding="utf-8").write("\n".join(lines))
print("odkaz vložen za řádek", hits[0]+1)
PY
fi
[ "$(grep -c 'href="/zabijacka/"' "$IDX")" = "1" ] || rollback
grep -n 'href="/zabijacka/"' "$IDX"

step "5 restart $LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL" || rollback
UP=""
for i in $(seq 1 25); do
  if lsof -nP -iTCP:8017 -sTCP:LISTEN >/dev/null 2>&1 && curl -s -o /dev/null http://127.0.0.1:8017/health; then UP=1; break; fi
  sleep 1
done
[ -n "$UP" ] || { tail -20 "$ERRLOG"; rollback; }
lsof -nP -iTCP:8017 -sTCP:LISTEN | head -2

step "6 ověření lokálně (cf-connecting-ip = simulace internetu, tj. basic auth)"
EXT=(-H "cf-connecting-ip: 1.2.3.4")
c(){ printf '%-58s' "$1"; shift; curl -s -o /tmp/zb_body -w "%{http_code} %{content_type}" "$@"; echo " | $(head -c 60 /tmp/zb_body | tr '\n' ' ')"; }
c "GET /zabijacka/ (ext) -> 200 text/html"         "${EXT[@]}" http://127.0.0.1:8017/zabijacka/
grep -q "Zabijačka na zámku" /tmp/zb_body || rollback
c "GET /zabijacka/state.json (ext) -> 200 json"    "${EXT[@]}" http://127.0.0.1:8017/zabijacka/state.json
c "GET / (ext, bez auth) -> 401"                    "${EXT[@]}" http://127.0.0.1:8017/
c "GET /zabijackax (ext) -> 401"                    "${EXT[@]}" http://127.0.0.1:8017/zabijackax
c "GET / (LAN) obsahuje odkaz -> 200"               http://127.0.0.1:8017/
grep -c 'href="/zabijacka/"' /tmp/zb_body | sed 's/^/  odkazů na \/zabijacka\/ v kořeni: /'

step "7 ověření zvenku přes Cloudflare (bez auth)"
c "GET $PUB/zabijacka/ -> 200"                      "$PUB/zabijacka/"
grep -q "Zabijačka na zámku" /tmp/zb_body && echo "  tělo obsahuje 'Zabijačka na zámku': OK"
c "GET state.json -> 200 json"                      "$PUB/zabijacka/state.json"
c "POST test tick -> 200 {\"ok\":true}"             -H 'Content-Type: application/json' -d '{"ticks":{"0-0":true},"updated":"2026-09-17T00:00:00Z"}' "$PUB/zabijacka/state.json"
c "GET po POST -> obsahuje 0-0"                     "$PUB/zabijacka/state.json"
grep -q '"0-0"' /tmp/zb_body && echo "  0-0 uloženo: OK"
c "POST reset (čistý seznam pro Miloše)"            -H 'Content-Type: application/json' -d '{"ticks":{},"updated":null}' "$PUB/zabijacka/state.json"
c "GET po resetu"                                   "$PUB/zabijacka/state.json"
c "GET $PUB/ bez auth -> 401"                       "$PUB/"
if [ -n "${CITOLIBY_BASIC_PASS:-}" ]; then
  c "GET $PUB/ s basic auth -> 200"                 -u "${CITOLIBY_BASIC_USER:-citoliby}:$CITOLIBY_BASIC_PASS" "$PUB/"
  grep -c 'href="/zabijacka/"' /tmp/zb_body | sed 's/^/  odkazů na \/zabijacka\/ přes auth: /'
else
  echo "  (kořen s basic auth: spusť s CITOLIBY_BASIC_PASS=... v env, jinak ověř ručně v prohlížeči)"
fi

step "8 git"
for R in "$D" /Users/investimenti/castello-citoliby; do
  TOP=$(git -C "$R" rev-parse --show-toplevel 2>/dev/null) || { echo "$R: není v gitu"; continue; }
  echo "$R: repo $TOP"
  if [ "$R" = "$D" ]; then
    git -C "$R" add backend.py zabijacka/index.html
    git -C "$R" -c user.name="Elias Marold" -c user.email="elias.marold@investimenti.cz" commit -q -m "citoliby-d: zabijacka checklist + state.json" && git -C "$R" log -1 --format="  %h %an <%ae> %s" || echo "  nic ke commitu"
  else
    git -C "$R" add internal/index_d.html
    git -C "$R" -c user.name="Elias Marold" -c user.email="elias.marold@investimenti.cz" commit -q -m "citoliby-d: zabijacka checklist odkaz v index_d.html" && git -C "$R" log -1 --format="  %h %an <%ae> %s" || echo "  nic ke commitu"
  fi
done

step "9 záloha na fortress (D-080) — jen zjištění mechanismu"
grep -rln "citoliby_visual_archive" /Users/investimenti/andrew_core/scripts /Users/investimenti/andrew_core/audits/RUNBOOK_MAC.md /Users/investimenti/Library/LaunchAgents 2>/dev/null | head
crontab -l 2>/dev/null | grep -i -E "citoliby|backup|fortress" || echo "  (crontab: nic)"
echo "  Ručně: rsync -av $D/zabijacka/ ubuntu@fortress:/home/ubuntu/backups/citoliby_d_zabijacka/  (a backend.py + .bak)"

step "HOTOVO"
echo "URL pro Miloše: $PUB/zabijacka/"
echo "Bible fact k zapsání (topic:citoliby): zabijačka checklist: $PUB/zabijacka/ (veřejné bez auth, sdílený stav v zabijacka/state.json, zdroj dave.investimenti.cz/p/-nUT7NfwujV7HZFm_DCDjc9fcGcz4Hwx, 17.9.2026)"
