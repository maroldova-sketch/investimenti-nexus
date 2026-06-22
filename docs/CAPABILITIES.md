# NEXUS × Elias — kompletní výpis schopností a funkcí

Stav k tomuto PR. Generováno z reálných rout aplikace (141 endpointů) + MCP
nástroje, skripty, integrace a self-heal. Členěno podle vrstev.

---

## 1. Strojové rozhraní pro Elias / MCP / n8n  (`/api/v1/*`, API-key + scopes)

Autentizace: hlavička `X-API-Key: nxs_...` nebo `Authorization: Bearer nxs_...`.

| Endpoint | Metoda | Scope | Funkce |
|----------|--------|-------|--------|
| `/api/v1/ping` | GET | (jakýkoli) | identita tokenu + jeho scopes |
| `/api/v1/atlas/kpis` | GET | `fortis:read` | KPI holdingu (headcount, PHM, otevřené pokuty/pojistky/srážky, nové notifikace) |
| `/api/v1/fleet/vehicles` | GET | `fleet:read` | seznam vozidel (filtr status, limit) |
| `/api/v1/people` | GET | `people:read` | seznam osob/zaměstnanců |
| `/api/v1/fortis/documents` | GET | `fortis:read` | ekonomické doklady (filtr status/doc_type) |
| `/api/v1/notifications` | GET | `notify:read` | čtení notifikací |
| `/api/v1/notifications` | POST | `notify:write` | vytvoření in-app notifikace |
| `/api/v1/mail/send` | POST | `mail:send` | odeslání e-mailu přes M365 |
| `/api/v1/imports/{name}/run` | POST | `imports:run` | spuštění importu (`fleet` / `fuel`) |
| `/api/v1/idoklad/ping` | GET | `idoklad:read` | ověření iDoklad creds |
| `/api/v1/idoklad/invoices` | GET | `idoklad:read` | faktury z iDokladu (received/issued) |
| `/api/v1/idoklad/sync` | POST | `idoklad:write` | sync faktur iDoklad → Fortis |

**Scopes:** `fleet:read · people:read · fortis:read · notify:read · notify:write ·
mail:send · idoklad:read · idoklad:write · imports:run · admin` (admin = vše).

---

## 2. MCP nástroje  (`mcp/nexus_mcp.py` — pro Claude relaci / mobil)

| Nástroj | Scope | Co dělá |
|---------|-------|---------|
| `nexus_ping` | – | identita + scopes klíče |
| `atlas_kpis` | fortis:read | KPI holdingu |
| `fleet_vehicles` | fleet:read | seznam vozidel |
| `people` | people:read | seznam osob |
| `fortis_documents` | fortis:read | ekonomické doklady |
| `notifications` | notify:read | čtení notifikací |
| `create_notification` | notify:write | vytvoření notifikace |
| `send_mail` | mail:send | odeslání e-mailu (M365) |
| `run_import` | imports:run | spuštění importu (fleet/fuel) |
| `idoklad_invoices` | idoklad:read | faktury z iDokladu |
| `idoklad_sync` | idoklad:write | sync iDoklad → Fortis |

Transport: **stdio** (lokálně) i **streamable-HTTP** (mobil/claude.ai přes cloudflared).

---

## 3. Webové moduly (HTML UI, cookie auth, role-based)

### 🛰️ Atlas — velín / dashboard
- `/atlas` přehled, `/atlas/api/kpis` JSON KPI

### 🚗 Fleet — vozový park
- Vozidla: seznam `/fleet`, detail `/fleet/{id}`, edit, události, přiřazení řidiče
- Řidiči: `/fleet/drivers`, detail `/fleet/driver/{id}`, zápis tachometru
- PHM: `/fleet/phm` (spotřeba/anomálie)
- Jízdy: `/fleet/trips` + new/approve/ignore
- Srážky: `/fleet/deductions`, nová, approve, export (i batch)
- Completion (pojistné události): `/fleet/completion`, claim handling
- Pokuty: `/fleet/{id}/fine/new`; Pojistky: `/fleet/{id}/claim/new`
- Axigon kontakty: `/fleet/axigon`, set-primary, toggle

### 👥 People — osoby / HR
- Seznam `/people`, detail `/people/{id}`, edit, nová osoba
- Smlouvy: `/people/{id}/contracts` + new/deactivate
- Zaměstnání, membership (entity), role assignment
- Merge duplicit: `/people/merge`, `/people/merge/{a}/{b}`, execute

### 🕒 Attendance — docházka
- Období `/attendance`, detail `/attendance/{period}`
- new, save-row, submit, approve, lock, export

### 🏖️ Leave — dovolené / absence
- `/leave` + new / approve / reject

### 📥 Import — staging pipeline
- Dávky `/import`, detail `/import/{batch}`
- Sekce fleet / fuel / people / payroll / issues
- Akce: link, apply, ignore, mark-new, assign, resolve
- Rychlé spuštění: `/import/run/fleet`, `/import/run/fuel`

### 📨 Intake — ruční příjem podnětů
- `/intake`, nový, detail, review, ignore
- Konverze: → claim / → fine / → odometer

### 🔔 Notifications — notifikační centrum
- `/notifications` přehled
- Generátory: odometer / compliance / deductions / fuel / all
- Akce: read / acknowledge / close

### 📧 M365 — Microsoft 365
- Mail: inbox, detail, search, compose, **send**
- Kalendář `/m365/calendar`, kontakty, soubory (Drive)
- API varianty `/m365/api/*` (mail, calendar, contacts, files, me, capabilities)

### 🏛️ Gov — ISDS datové schránky
- `/gov/api/schranky`, `/gov/api/messages`, poll, download zprávy

### 📅 Calendar — kalendář
- `/calendar`, svátky/jmeniny dne, nový event

### ✅ Approvals — schvalování
- `/approvals` přehled schvalovacích případů

### 🔐 Auth — přihlášení
- login / logout (JWT cookie / Bearer)

---

## 4. Webhooky — strukturovaný příjem (HMAC podpis)

Autentizace: `X-Nexus-Signature: sha256=<hmac>` (klíč `WEBHOOK_SECRET`).

| Endpoint | Typ podnětu |
|----------|-------------|
| `POST /webhooks/intake/odometer` | odečet tachometru |
| `POST /webhooks/intake/fine` | pokuta |
| `POST /webhooks/intake/claim` | pojistná událost |
| `POST /webhooks/intake/service` | servis |
| `POST /webhooks/intake/tires` | pneu |
| `POST /webhooks/intake/general` | obecný podnět |
| `GET /webhooks/intake/contract` | kontrakt/schéma |

Pipeline: validace → resolve telefon→osoba→vozidlo → intake_record → audit.

---

## 5. Integrace

| Systém | Stav | Rozsah |
|--------|------|--------|
| **Microsoft 365** (Graph) | ✅ | mail (číst/hledat/poslat), kalendář, kontakty, Drive |
| **iDoklad** | ✅ čtení + sync | OAuth2, faktury received/issued → Fortis |
| **ISDS** (datové schránky) | ✅ | poll, zprávy, download |
| **Axigon** | ✅ | fleet kontakty/import |
| **Elias dispatcher** | ✅ jednosměrně | Nexus → Teams/Planner (gov/approval/fuel anomálie) |
| **Telegram** | ✅ | notifikace z heal scriptu |
| **n8n / HA** | ⏳ MCP | externí, hlídá heal |

---

## 6. Skripty / CLI

| Skript | Funkce |
|--------|--------|
| `scripts/nexus_token.py` | správa API tokenů: create / list / revoke |
| `scripts/elias_mcp_heal.sh` | health-check + self-heal MCP/bridge služeb |
| `scripts/import_fleet.py` | import vozového parku |
| `scripts/import_fuel.py` | import PHM transakcí |
| `scripts/seed.py` | seed dat |
| `mcp/nexus_mcp.py` | Nexus MCP server |

### Self-heal (`elias_mcp_heal.sh`)
- Probe endpointů (local/cloud) → klasifikace UP/AUTH/DEGRADED/DOWN
- Restart lokálních služeb: systemd / docker / launchd (auto-discovery)
- iDoklad token check
- Endpointy z `registry.json`
- Notifikace: Telegram + zápis do Nexus notifikací
- Instalace timeru: systemd / LaunchAgent
- Režimy: `--report` / heal / `--install-timer` / `--help`

---

## 7. Bezpečnost

- **API tokeny:** v DB jen pbkdf2 hash, plný `nxs_...` jen při vytvoření, scopes, expiry, revoke
- **Webhooky:** HMAC podpis (`WEBHOOK_SECRET`)
- **UI:** JWT (cookie/Bearer), role owner/admin/manager/hr/finance/fleet_manager/readonly
- **Hesla:** pbkdf2-sha256 (260k iterací)
- **Audit:** `audit_log` (kdo/co/kdy), API akce logovány jako `api:<token>`

---

## 8. Co ještě chybí (mimo tento repo)

Viz `docs/ARCHITECTURE_ELIAS.md` §"Co ještě CHYBÍ":
cloudflared tunel pro `nexus-mcp` · registry jako jediný zdroj pravdy ·
verzování n8n workflows · iDoklad write (vystavení/úhrada) · víc M365 schránek ·
centralizace secrets · cross-system audit · MCP tool-level health.
