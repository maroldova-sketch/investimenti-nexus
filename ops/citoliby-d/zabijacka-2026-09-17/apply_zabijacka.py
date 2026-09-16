#!/usr/bin/env python3
"""Aplikuje úpravu 'zabijacka' na sites/citoliby-d/backend.py (anchor-based, idempotentní)."""
import sys, pathlib
p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "backend.py")
src = p.read_text(encoding="utf-8")
if "ZABIJACKA_DIR" in src:
    print("already applied"); sys.exit(0)

ROUTES = '''# ===== Zabijačka: veřejný zaklikávací checklist + sdílený stav (2026-09-17) =====
# zabijacka/index.html leží vedle backend.py, state.json vedle něj.
# Prefix /zabijacka/ je vyňatý z basic auth (viz níže u _attach_auth) — jen tento prefix, nic jiného.
import json as _json
import tempfile as _tempfile
from fastapi.responses import JSONResponse

ZABIJACKA_DIR = pathlib.Path(__file__).resolve().parent / "zabijacka"
ZABIJACKA_INDEX = ZABIJACKA_DIR / "index.html"
ZABIJACKA_STATE = ZABIJACKA_DIR / "state.json"
ZABIJACKA_MAX_BYTES = 64 * 1024
_ZABIJACKA_EMPTY = '{"ticks":{},"updated":null}'
_ZABIJACKA_NO_STORE = {"Cache-Control": "no-store"}


def _zabijacka_valid(data) -> bool:
    """Přesně {ticks: {str: true, ...}, updated: str|null}; nic jiného."""
    if not isinstance(data, dict) or set(data.keys()) != {"ticks", "updated"}:
        return False
    ticks, updated = data["ticks"], data["updated"]
    if not isinstance(ticks, dict) or not all(isinstance(k, str) and v is True for k, v in ticks.items()):
        return False
    return updated is None or isinstance(updated, str)


@app.get("/zabijacka/")
@app.get("/zabijacka/index.html")
async def zabijacka_index():
    if not ZABIJACKA_INDEX.exists():
        return HTMLResponse("<h1>zabijacka/index.html chybí</h1>", status_code=404)
    return HTMLResponse(ZABIJACKA_INDEX.read_text(encoding="utf-8"))


@app.get("/zabijacka/state.json")
async def zabijacka_state_get():
    body = _ZABIJACKA_EMPTY
    if ZABIJACKA_STATE.exists():
        try:
            raw = ZABIJACKA_STATE.read_text(encoding="utf-8")
            _json.loads(raw)
            body = raw
        except Exception:
            body = _ZABIJACKA_EMPTY
    return Response(content=body, media_type="application/json", headers=_ZABIJACKA_NO_STORE)


@app.post("/zabijacka/state.json")
async def zabijacka_state_post(request: Request):
    def bad(msg):
        return JSONResponse({"ok": False, "error": msg}, status_code=400, headers=_ZABIJACKA_NO_STORE)
    cl = request.headers.get("content-length", "")
    if cl.isdigit() and int(cl) > ZABIJACKA_MAX_BYTES:
        return bad("too large")
    raw = await request.body()
    if len(raw) > ZABIJACKA_MAX_BYTES:
        return bad("too large")
    try:
        data = _json.loads(raw)
    except Exception:
        return bad("invalid json")
    if not _zabijacka_valid(data):
        return bad("invalid state")
    ZABIJACKA_DIR.mkdir(parents=True, exist_ok=True)
    payload = _json.dumps({"ticks": data["ticks"], "updated": data["updated"]}, ensure_ascii=False)
    fd, tmp = _tempfile.mkstemp(prefix=".state.", suffix=".tmp", dir=ZABIJACKA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, ZABIJACKA_STATE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return JSONResponse({"ok": True}, headers=_ZABIJACKA_NO_STORE)
# ===== END Zabijačka =====


'''
ANCHOR_ROUTES = '@app.get("/{path:path}")\nasync def passthrough(path: str):'
assert src.count(ANCHOR_ROUTES) == 1, "anchor passthrough not found"
src = src.replace(ANCHOR_ROUTES, ROUTES + ANCHOR_ROUTES)

OLD_AUTH = '# W8 — attach split-brain auth\n_attach_auth(app, realm="Citoliby Liveboard - interni")\n'
NEW_AUTH = '''# W8 — attach split-brain auth
# Zabijačka: prefix /zabijacka/ je veřejný (bez basic auth). Platí jen pro tento proces —
# sdílená lib/split_brain_auth.py zůstává beze změny (middleware čte FREE_PATH_PREFIXES za běhu).
import split_brain_auth as _sba
if "/zabijacka/" not in _sba.FREE_PATH_PREFIXES:
    _sba.FREE_PATH_PREFIXES = _sba.FREE_PATH_PREFIXES + ("/zabijacka/",)
_attach_auth(app, realm="Citoliby Liveboard - interni")
'''
assert src.count(OLD_AUTH) == 1, "anchor auth not found"
src = src.replace(OLD_AUTH, NEW_AUTH)
p.write_text(src, encoding="utf-8")
print("applied", p)
