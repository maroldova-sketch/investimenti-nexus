#!/usr/bin/env python3
"""NEXUS MCP server — vystavuje Nexus jako MCP nástroje pro Elias.

Obaluje strojové JSON API (/api/v1/*). Sám nedrží žádnou logiku ani DB —
jen překládá MCP tool-call → HTTP volání na Nexus s API-key.

Env:
    NEXUS_API_BASE   default http://127.0.0.1:8000   (kořen Nexus FastAPI)
    NEXUS_API_KEY    nxs_... (vytvoř přes scripts/nexus_token.py)
    NEXUS_MCP_HTTP   pokud "1" → běží jako streamable-HTTP (pro mobil/cloud přes tunel)
    NEXUS_MCP_PORT   default 8791  (jen pro HTTP režim)

Spuštění:
    # lokální stdio (Claude Desktop / Elias):
    NEXUS_API_KEY=nxs_... python mcp/nexus_mcp.py
    # remote HTTP (za cloudflared tunelem → mobil / claude.ai):
    NEXUS_MCP_HTTP=1 NEXUS_API_KEY=nxs_... python mcp/nexus_mcp.py

Závislosti: pip install -r mcp/requirements.txt
"""
import os
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("NEXUS_API_BASE", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.environ.get("NEXUS_API_KEY", "")

mcp = FastMCP("nexus")


def _client() -> httpx.Client:
    if not API_KEY:
        raise RuntimeError("NEXUS_API_KEY není nastaven")
    return httpx.Client(base_url=API_BASE, headers={"X-API-Key": API_KEY}, timeout=30)


def _get(path: str, params: Optional[dict] = None) -> Any:
    with _client() as c:
        r = c.get(path, params=params or {})
        r.raise_for_status()
        return r.json()


def _post(path: str, body: Optional[dict] = None, params: Optional[dict] = None) -> Any:
    with _client() as c:
        r = c.post(path, json=body or {}, params=params or {})
        r.raise_for_status()
        return r.json()


# ── nástroje (read) ─────────────────────────────────────────────────────────
@mcp.tool()
def nexus_ping() -> dict:
    """Ověří spojení a vrátí identitu/scopes API klíče."""
    return _get("/api/v1/ping")


@mcp.tool()
def atlas_kpis() -> dict:
    """Klíčové KPI holdingu (headcount, PHM, otevřené pojistky/pokuty/srážky, notifikace)."""
    return _get("/api/v1/atlas/kpis")


@mcp.tool()
def fleet_vehicles(status: Optional[str] = None, limit: int = 200) -> dict:
    """Seznam vozidel (volitelně filtr status, např. ACTIVE)."""
    return _get("/api/v1/fleet/vehicles", {"status": status, "limit": limit})


@mcp.tool()
def people(active_only: bool = True, limit: int = 200) -> dict:
    """Seznam osob (zaměstnanci)."""
    return _get("/api/v1/people", {"active_only": active_only, "limit": limit})


@mcp.tool()
def fortis_documents(status: Optional[str] = None, doc_type: Optional[str] = None,
                     limit: int = 100) -> dict:
    """Ekonomické doklady (Fortis) — faktury/náklady, volitelně filtr."""
    return _get("/api/v1/fortis/documents",
                {"status": status, "doc_type": doc_type, "limit": limit})


@mcp.tool()
def notifications(status: Optional[str] = None, limit: int = 50) -> dict:
    """Notifikace z Nexusu (volitelně filtr status, např. new)."""
    return _get("/api/v1/notifications", {"status": status, "limit": limit})


@mcp.tool()
def idoklad_invoices(kind: str = "received", pages: int = 1) -> dict:
    """Faktury z iDokladu (kind=received|issued)."""
    return _get("/api/v1/idoklad/invoices", {"kind": kind, "pages": pages})


# ── nástroje (write) ────────────────────────────────────────────────────────
@mcp.tool()
def create_notification(title: str, body: str = "", severity: str = "info",
                        related_type: str = "general") -> dict:
    """Vytvoří in-app notifikaci v Nexusu (severity: info|warn|error)."""
    return _post("/api/v1/notifications", {
        "title": title, "body": body, "severity": severity, "related_type": related_type})


@mcp.tool()
def send_mail(to: str, subject: str, body: str) -> dict:
    """Odešle e-mail přes M365 (to = adresa nebo čárkou oddělené adresy)."""
    return _post("/api/v1/mail/send", {"to": to, "subject": subject, "body": body})


@mcp.tool()
def run_import(name: str) -> dict:
    """Spustí import v Nexusu (name: fleet|fuel)."""
    return _post(f"/api/v1/imports/{name}/run")


@mcp.tool()
def idoklad_sync(kind: str = "received", pages: int = 2) -> dict:
    """Stáhne faktury z iDokladu a zapíše je do Fortis (kind=received|issued)."""
    return _post("/api/v1/idoklad/sync", params={"kind": kind, "pages": pages})


if __name__ == "__main__":
    if os.environ.get("NEXUS_MCP_HTTP") == "1":
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = int(os.environ.get("NEXUS_MCP_PORT", "8791"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run()  # stdio
