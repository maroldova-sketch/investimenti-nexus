# T3 — Gap report (dosah → mobil/chat přes MCP)

Datum: 2026-06-22. Pro každý systém z T1: je vystavený jako MCP nástroj pro
mobil/chat? Pokud ne a dává smysl → minimální návrh expozice.

## Přehled expozice

| Systém | MCP pro mobil/chat? | Poznámka |
|--------|---------------------|----------|
| NEXUS (čtení) | ✅ částečně | `nexus-mcp`: atlas/fleet/people/fortis/notifications/idoklad |
| NEXUS (zápis) | ⚠️ minimum | jen `create_notification`, `run_import`, `idoklad_sync` |
| bible-api | ✅ | `bible-mcp` (veřejně přes cloudflared) |
| Home Assistant | ✅ | `ha-klod-mcp` (Nabu Casa) |
| n8n | ✅ | `n8n-mcp` (cloud) |
| M365 maily/kalendář (čtení) | ❌ | `send_mail` ano, **čtení inboxu/kalendáře/kontaktů ne** |
| ISDS / datové schránky (gov) | ❌ | žádný MCP nástroj |
| registry / discovery | ❌ | katalog služeb se z chatu nedá dotázat |
| Cloudflare | ❌ | správa tunelů/DNS z chatu (nízká priorita) |

---

## 🔴 GAP 0 (SECURITY, blokující) — nechráněné public routy

Introspekce běžící app (`scripts/nexus_inventory.py`) odhalila routy **bez
jakékoli autentizace**, které spouští citlivé akce:

| Route | Riziko |
|-------|--------|
| `POST /gov/api/poll` | kdokoli spustí poll datových schránek |
| `POST /gov/api/messages/{id}/download` | stažení úředních zpráv (ZFO+přílohy) bez auth |
| `GET /gov/api/messages`, `/gov/api/schranky` | výpis ISDS metadat bez auth |
| `GET /import/run/fleet`, `/import/run/fuel` | spuštění importu přes GET (CSRF-able) |

**Fix:** přidat `Depends(get_current_user)` (UI) **nebo** `require_scope(...)`
(stroj) na tyto routy; import triggery převést z GET na POST. Malá změna,
vysoká priorita — udělat dřív než cokoli vystavíme na mobil.

---

## 🟠 GAP 1 — M365 čtení mailů/kalendáře není v MCP

Elias z mobilu umí mail **poslat**, ale ne **přečíst** inbox / vyhledat / vidět
kalendář. Kód v `backend/integrations/m365/client.py` to umí (`list_messages`,
`search_messages`, `list_events`, `list_contacts`), jen není vystavený.

**Fix (minimální):**
- API: `GET /api/v1/mail/inbox`, `GET /api/v1/mail/search`,
  `GET /api/v1/calendar/events` — scope **`mail:read`** (nový)
- MCP nástroje: `mail_inbox`, `mail_search`, `calendar_events`
- Cílí na schránku dle `M365_MAILBOX` (app režim) — funguje pro produkce@…

## 🟠 GAP 2 — ISDS (datové schránky) není v MCP

Úřední komunikace je vysoká hodnota a momentálně mimo chat. Navíc dnes běží
bez auth (viz GAP 0).

**Fix (minimální):**
- API: `GET /api/v1/gov/messages` (scope **`gov:read`**),
  `POST /api/v1/gov/poll` (scope **`gov:write`**)
- MCP nástroje: `gov_messages`, `gov_poll`
- Existující `/gov/api/*` ponechat pro UI, ale zabezpečit.

## 🟡 GAP 3 — Registry/discovery se z chatu nedá dotázat

`registry` (192.168.1.43:8110) drží katalog služeb, ale Elias na mobilu nemá
nástroj „co je dostupné / kde co běží". Heal script už `registry.json` čte —
chybí read-only MCP pohled.

**Fix (minimální):**
- API: `GET /api/v1/registry/services` (scope `notify:read` nebo nový `infra:read`)
  — vrátí katalog + poslední stav z heal logu
- MCP nástroj: `services_catalog` → Elias si na mobilu ověří dosah sám.

## 🟡 GAP 4 — NEXUS zápisové operace v MCP jen minimální

Z chatu nejdou běžné akce (schválení srážky, zápis tachometru mimo webhook,
vytvoření události). Záměrně opatrně — zápis přes agenta chce scopes + audit.

**Fix (návrh, vyžaduje design):**
- Začít nízkorizikovými: `POST /api/v1/fleet/odometer` (scope `fleet:write`),
  `POST /api/v1/calendar/event` (scope `calendar:write`)
- MCP nástroje `submit_odometer`, `create_event`
- Vše přes existující `audit_log` (akce `api:<token>`).

---

## Checkpoint T3 — 5 konkrétních děr

1. **GAP 0** nechráněné `/gov/api/*` + `/import/run/*` → přidat auth (blokující).
2. **GAP 1** M365 čtení → `mail:read` + nástroje `mail_inbox/mail_search/calendar_events`.
3. **GAP 2** ISDS → `gov:read/gov:write` + `gov_messages/gov_poll`.
4. **GAP 3** discovery → `services_catalog` MCP nástroj.
5. **GAP 4** zápisy → postupně `fleet:write`/`calendar:write` s auditem.

Pořadí realizace: **0 → 1 → 2 → 3 → 4**. GAP 0 je čistá bezpečnost a měl by jít
do samostatného rychlého PR.
