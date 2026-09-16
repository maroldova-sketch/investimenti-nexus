import urllib.request, re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pathlib, os

# ===== W8: Unified split-brain auth (Tailscale/LAN free, Internet=Basic Auth) =====
import sys as _sys
_sys.path.insert(0, "/Users/investimenti/andrew_core/lib")
import os as _os
import pathlib as _pl
# Load ~/andrew/.env into os.environ if not already
_env = _pl.Path.home() / "andrew" / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _, _v = _line.partition("=")
            _k = _k.strip(); _v = _v.strip().strip('"').strip("'")
            _os.environ.setdefault(_k, _v)
from split_brain_auth import attach_auth as _attach_auth
# ===== END W8 prep =====

HTML_PATH = pathlib.Path("/Users/investimenti/castello-citoliby/internal/index_d.html")
ARCH_PATH = pathlib.Path("/Users/investimenti/andrew_core/CITOLIBY_ARCHITECTURE.md")
NAVOD_PATH = pathlib.Path("/Users/investimenti/andrew_core/CITOLIBY_NAVOD.md")
ORIGIN = "https://citoliby.investimenti.cz"

app = FastAPI(title="Citoliby D-variant + docs")
app.mount("/audio", StaticFiles(directory="/Users/investimenti/castello-citoliby/assets/audio"), name="audio")

# (W8: old TIER middleware removed; replaced by split_brain_auth)

# Strip founders-only sections for team users
_TIER_STRIP_RX = re.compile(
    r"\s*<!--\s*TIER:founders:start\s*-->.*?<!--\s*TIER:founders:end\s*-->\s*",
    re.S,
)
def strip_founders(html: str) -> str:
    return _TIER_STRIP_RX.sub("\n", html)

def inject_banner(html: str, email: str, tier: str) -> str:
    """Decentní hlavička: kdo jsem + úroveň přístupu + odhlášení."""
    badge_color = "#b68a42" if tier == "founders" else "#7c8b6f"
    badge_text = "FOUNDERS" if tier == "founders" else "TEAM"
    label = "LAN" if email == "lan" else email
    logout_link = "" if email == "lan" else '&nbsp;·&nbsp;<a href="/cdn-cgi/access/logout" style="color:#bbb09e;text-decoration:none;">odhlásit</a>'
    banner = (
        f'<div style="position:fixed;top:0;right:0;z-index:9999;background:#0d0908;'
        f'padding:6px 14px;border-bottom-left-radius:6px;border-left:1px solid #3a3025;'
        f'border-bottom:1px solid #3a3025;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;letter-spacing:1px;color:#bbb09e;">'
        f'<span style="display:inline-block;background:{badge_color};color:#1a1410;'
        f'padding:1px 6px;border-radius:2px;font-weight:600;">{badge_text}</span>'
        f'&nbsp;·&nbsp;{label}{logout_link}'
        f'</div>'
    )
    # Vlož hned za <body>
    return re.sub(r"(<body[^>]*>)", r"\1" + banner, html, count=1, flags=re.I)


def render_md_page(title, md_text):
    return f"""<!doctype html><html lang="cs"><head>
<meta charset="utf-8"><title>{title} — Cítoliby</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root {{ --ink:#e8e2d4; --ink-2:#bbb09e; --ink-3:#857a68; --gold:#b68a42; --bg:#1a1410; --bg-card:#211a14; --line:#3a3025; --serif:"Cormorant Garamond",Georgia,serif; --sans:Inter,sans-serif; --mono:"JetBrains Mono",monospace; }}
  body {{ background:var(--bg); color:var(--ink-2); font-family:var(--sans); font-size:15px; line-height:1.65; margin:0; padding:0; }}
  .container {{ max-width: 820px; margin:0 auto; padding:48px 32px 80px; }}
  .topbar {{ background:#0d0908; padding:14px 32px; border-bottom:1px solid var(--line); font-family:var(--mono); font-size:11px; letter-spacing:2px; }}
  .topbar a {{ color:var(--gold); text-decoration:none; }}
  h1 {{ font-family:var(--serif); color:var(--ink); font-weight:500; font-size:36px; letter-spacing:-0.02em; margin:0 0 8px; }}
  h2 {{ font-family:var(--serif); color:var(--ink); font-weight:500; font-size:24px; letter-spacing:-0.01em; margin:36px 0 12px; padding-bottom:8px; border-bottom:1px solid var(--line); }}
  h3 {{ font-family:var(--serif); color:var(--gold); font-weight:500; font-size:18px; margin:24px 0 8px; }}
  a {{ color:var(--gold); }}
  code {{ font-family:var(--mono); font-size:13px; background:#0d0908; padding:2px 6px; border-radius:3px; color:var(--ink); }}
  pre {{ background:#0d0908; padding:16px; border-radius:4px; overflow-x:auto; border:1px solid var(--line); font-family:var(--mono); font-size:12px; line-height:1.55; }}
  pre code {{ background:none; padding:0; }}
  table {{ border-collapse:collapse; width:100%; margin:12px 0; font-size:13px; }}
  th {{ text-align:left; padding:8px 10px; background:#0d0908; color:var(--gold); font-family:var(--mono); font-size:11px; letter-spacing:1px; text-transform:uppercase; border-bottom:1px solid var(--line); }}
  td {{ padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  blockquote {{ border-left:3px solid var(--gold); padding:8px 16px; margin:16px 0; background:#0d0908; color:var(--ink); font-style:italic; }}
  ul, ol {{ padding-left:24px; }}
  li {{ margin:4px 0; }}
  hr {{ border:none; border-top:1px solid var(--line); margin:32px 0; }}
  .badge {{ display:inline-block; padding:2px 8px; background:var(--gold); color:#1a1410; font-family:var(--mono); font-size:10px; letter-spacing:1.5px; font-weight:600; border-radius:2px; }}
</style>
</head><body>
<div class="topbar">
  <a href="/">← CÍTOLIBY MASTER LIVEBOARD</a>
</div>
<div class="container">
{md_text}
</div>
</body></html>"""


def md_to_html(md):
    import re, html
    lines = md.split("\n")
    out = []
    in_code = False; in_list = False; in_table = False
    for line in lines:
        if line.startswith("```"):
            if in_code: out.append("</code></pre>"); in_code = False
            else: out.append("<pre><code>"); in_code = True
            continue
        if in_code: out.append(html.escape(line)); continue
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r"^[-:\s]+$", c) for c in cells): continue
            if not in_table:
                out.append("<table>"); in_table = True
                out.append("<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
            else:
                out.append("<tr>" + "".join(f"<td>{render_inline(c)}</td>" for c in cells) + "</tr>")
            continue
        elif in_table: out.append("</table>"); in_table = False
        if line.startswith("### "): out.append(f"<h3>{render_inline(line[4:])}</h3>")
        elif line.startswith("## "): out.append(f"<h2>{render_inline(line[3:])}</h2>")
        elif line.startswith("# "): out.append(f"<h1>{render_inline(line[2:])}</h1>")
        elif line.startswith("> "): out.append(f"<blockquote>{render_inline(line[2:])}</blockquote>")
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list: out.append("<ul>"); in_list = True
            out.append(f"<li>{render_inline(line[2:])}</li>")
        elif line.startswith("---"):
            if in_list: out.append("</ul>"); in_list = False
            out.append("<hr>")
        elif line.strip() == "":
            if in_list: out.append("</ul>"); in_list = False
            out.append("")
        else:
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<p>{render_inline(line)}</p>")
    if in_list: out.append("</ul>")
    if in_table: out.append("</table>")
    if in_code: out.append("</code></pre>")
    return "\n".join(out)


def render_inline(s):
    import re, html
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


@app.get("/health")
async def health():
    return {"ok": True, "service": "citoliby-d-tiered", "html_size": HTML_PATH.stat().st_size if HTML_PATH.exists() else 0}


@app.get("/")
async def root(request: Request):
    html = HTML_PATH.read_text(encoding="utf-8")
    tier = getattr(request.state, "tier", "team")
    email = getattr(request.state, "email", "unknown")
    if tier == "team":
        html = strip_founders(html)
    html = inject_banner(html, email, tier)
    return HTMLResponse(html)


@app.get("/architecture")
async def architecture():
    if not ARCH_PATH.exists():
        return HTMLResponse("<h1>ARCHITECTURE.md not found</h1>", status_code=404)
    md = ARCH_PATH.read_text(encoding="utf-8")
    return HTMLResponse(render_md_page("Architektura", md_to_html(md)))


@app.get("/navod")
async def navod():
    if not NAVOD_PATH.exists():
        return HTMLResponse("<h1>NAVOD.md je teprve v přípravě</h1><p><a href=\"/\">← zpět</a></p>", status_code=200)
    md = NAVOD_PATH.read_text(encoding="utf-8")
    return HTMLResponse(render_md_page("Návod k použití", md_to_html(md)))


# ===== Zabijačka: veřejný zaklikávací checklist + sdílený stav (2026-09-17) =====
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


@app.get("/{path:path}")
async def passthrough(path: str):
    url = f"{ORIGIN}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            content = r.read()
            ctype = r.headers.get("Content-Type", "application/octet-stream")
            return Response(content=content, media_type=ctype)
    except Exception:
        return RedirectResponse(url)


# W8 — attach split-brain auth
# Zabijačka: prefix /zabijacka/ je veřejný (bez basic auth). Platí jen pro tento proces —
# sdílená lib/split_brain_auth.py zůstává beze změny (middleware čte FREE_PATH_PREFIXES za běhu).
import split_brain_auth as _sba
if "/zabijacka/" not in _sba.FREE_PATH_PREFIXES:
    _sba.FREE_PATH_PREFIXES = _sba.FREE_PATH_PREFIXES + ("/zabijacka/",)
_attach_auth(app, realm="Citoliby Liveboard - interni")
# === END W8 ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017, log_level="warning")
