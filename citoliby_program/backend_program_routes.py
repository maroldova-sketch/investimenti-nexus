# === PROGRAM (2026-09-16): program.json = zdroj pravdy pro tab PROGRAM; master dashboard ===
# Vkládá se do ~/andrew_core/sites/citoliby-d/backend.py PŘED catch-all @app.get("/{path:path}")
# (deploy_program.sh to dělá automaticky; tento soubor je jen zdroj bloku).
PROGRAM_JSON_PATH = pathlib.Path("/Users/investimenti/castello-citoliby/dashboard/data/program.json")
MASTER_PATH = pathlib.Path("/Users/investimenti/castello-citoliby/internal/index_master.html")


@app.get("/dashboard/data/program.json")
@app.get("/api/program")
async def program_json():
    if not PROGRAM_JSON_PATH.exists():
        return Response(content='{"error":"program.json not found"}', media_type="application/json", status_code=404)
    return FileResponse(PROGRAM_JSON_PATH, media_type="application/json", headers={"Cache-Control": "no-store"})


@app.get("/master")
async def master(request: Request):
    if not MASTER_PATH.exists():
        return HTMLResponse("<h1>index_master.html not found</h1>", status_code=404)
    html = MASTER_PATH.read_text(encoding="utf-8")
    tier = getattr(request.state, "tier", "team")
    email = getattr(request.state, "email", "unknown")
    if tier == "team":
        html = strip_founders(html)
    html = inject_banner(html, email, tier)
    return HTMLResponse(html)
# === END PROGRAM ===
