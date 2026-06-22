#!/usr/bin/env python3
"""NEXUS inventář z BĚŽÍCÍ app (ne z paměti).

Bootne FastAPI app, projde app.routes, u každé routy introspekcí zjistí
metodu, path, auth vrstvu a scope (z dependency závislostí), a vypíše
buď tabulku (stdout), nebo Markdown pro docs/CAPABILITIES.md (--md).

  python scripts/nexus_inventory.py            # tabulka + souhrn
  python scripts/nexus_inventory.py --md       # markdown na stdout
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _flatten_deps(dependant, seen=None):
    """Rekurzivně posbírá všechny dependency callables routy."""
    if seen is None:
        seen = []
    for dep in getattr(dependant, "dependencies", []):
        call = getattr(dep, "call", None)
        if call is not None:
            seen.append(call)
        _flatten_deps(dep, seen)
    return seen


def _scope_of(call):
    """Vytáhne scope string z closure require_scope._dep, pokud tam je."""
    closure = getattr(call, "__closure__", None) or []
    for cell in closure:
        try:
            val = cell.cell_contents
        except ValueError:
            continue
        if isinstance(val, str) and (":" in val or val == "admin"):
            return val
    return None


def classify_auth(route):
    """Vrátí (auth, scope) podle dependency vrstvy routy."""
    deps = _flatten_deps(route.dependant)
    names = {getattr(c, "__name__", "") for c in deps}
    if "verify_webhook_signature" in names:
        return "HMAC", None
    if "require_scope" in names or "_dep" in names or "get_service_token" in names:
        scope = None
        for c in deps:
            if getattr(c, "__name__", "") == "_dep":
                scope = _scope_of(c)
                if scope:
                    break
        return "API-key", scope
    if "get_current_user" in names:
        return "cookie/JWT", None
    return "public", None


def collect():
    import main
    from fastapi.routing import APIRoute
    rows = []
    for r in main.app.routes:
        if not isinstance(r, APIRoute):
            continue
        if r.path in ("/openapi.json",):
            continue
        methods = sorted(m for m in (r.methods or []) if m not in ("HEAD", "OPTIONS"))
        auth, scope = classify_auth(r)
        desc = (r.summary or (r.endpoint.__doc__ or "").strip().split("\n")[0]
                or r.name or "")
        for m in methods:
            rows.append({
                "method": m, "path": r.path, "auth": auth,
                "scope": scope or "", "desc": desc[:80],
            })
    rows.sort(key=lambda x: (x["path"], x["method"]))
    return rows


def mcp_tools():
    """Vyparsuje nástroje + scopes z mcp/nexus_mcp.py (statická analýza)."""
    import ast
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "mcp", "nexus_mcp.py")
    tools = []
    try:
        tree = ast.parse(open(path).read())
    except Exception:
        return tools
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            is_tool = any(
                (isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "tool")
                or getattr(d, "attr", "") == "tool"
                for d in node.decorator_list
            )
            if is_tool:
                doc = (ast.get_docstring(node) or "").split("\n")[0]
                tools.append((node.name, doc))
    return tools


def main_cli():
    rows = collect()
    tools = mcp_tools()
    md = "--md" in sys.argv
    if md:
        print(render_md(rows, tools))
    else:
        for r in rows:
            print(f"{r['method']:6} {r['path']:42} {r['auth']:12} {r['scope']:14} {r['desc']}")
        print(f"\nROUT: {len(rows)} | MCP nástrojů: {len(tools)}")
        by_auth = {}
        for r in rows:
            by_auth[r["auth"]] = by_auth.get(r["auth"], 0) + 1
        print("Auth rozpad:", ", ".join(f"{k}={v}" for k, v in sorted(by_auth.items())))


def render_md(rows, tools):
    from datetime import date
    out = []
    out.append("# NEXUS — pravdivý inventář schopností\n")
    out.append(f"_Generováno z BĚŽÍCÍ app (`scripts/nexus_inventory.py`) — {date.today().isoformat()}._\n")
    out.append(f"**Rout: {len(rows)} · MCP nástrojů: {len(tools)}**\n")

    # API (api-key) zvlášť — strojové rozhraní pro Elias
    api = [r for r in rows if r["auth"] == "API-key"]
    out.append("\n## Strojové API (API-key + scope) — pro Elias / MCP / n8n\n")
    out.append("| Method | Path | Scope | Popis |")
    out.append("|--------|------|-------|-------|")
    for r in api:
        out.append(f"| {r['method']} | `{r['path']}` | `{r['scope'] or '—'}` | {r['desc']} |")

    # webhooky
    wh = [r for r in rows if r["auth"] == "HMAC"]
    out.append("\n## Webhooky (HMAC podpis)\n")
    out.append("| Method | Path | Popis |")
    out.append("|--------|------|-------|")
    for r in wh:
        out.append(f"| {r['method']} | `{r['path']}` | {r['desc']} |")

    # MCP nástroje
    out.append("\n## MCP nástroje (`mcp/nexus_mcp.py`)\n")
    out.append("| Nástroj | Popis |")
    out.append("|---------|-------|")
    for name, doc in tools:
        out.append(f"| `{name}` | {doc} |")

    # HTML/UI a ostatní
    ui = [r for r in rows if r["auth"] in ("cookie/JWT", "public")]
    out.append(f"\n## Webové UI + veřejné routy ({len(ui)})\n")
    out.append("| Method | Path | Auth | Popis |")
    out.append("|--------|------|------|-------|")
    for r in ui:
        out.append(f"| {r['method']} | `{r['path']}` | {r['auth']} | {r['desc']} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main_cli()
