# NEXUS — pravdivý inventář schopností

_Generováno z BĚŽÍCÍ app (`scripts/nexus_inventory.py`) — 2026-06-22._

**Rout: 140 · MCP nástrojů: 11**


## Strojové API (API-key + scope) — pro Elias / MCP / n8n

| Method | Path | Scope | Popis |
|--------|------|-------|-------|
| GET | `/api/v1/atlas/kpis` | `fortis:read` | atlas_kpis |
| GET | `/api/v1/fleet/vehicles` | `fleet:read` | fleet_vehicles |
| GET | `/api/v1/fortis/documents` | `fortis:read` | fortis_documents |
| GET | `/api/v1/idoklad/invoices` | `idoklad:read` | invoices |
| GET | `/api/v1/idoklad/ping` | `idoklad:read` | idoklad_ping |
| POST | `/api/v1/idoklad/sync` | `idoklad:write` | Stáhne faktury z iDokladu a upsertne je do fortis_document (source_system=idokla |
| POST | `/api/v1/imports/{name}/run` | `imports:run` | run_import |
| POST | `/api/v1/mail/send` | `mail:send` | send_mail |
| GET | `/api/v1/notifications` | `notify:read` | list_notifications |
| POST | `/api/v1/notifications` | `notify:write` | Vytvoří in-app notifikaci. Používá např. heal script při výpadku služby. |
| GET | `/api/v1/people` | `people:read` | people |
| GET | `/api/v1/ping` | `—` | ping |

## Webhooky (HMAC podpis)

| Method | Path | Popis |
|--------|------|-------|
| POST | `/webhooks/intake/claim` | Structured insurance claim / incident report. |
| GET | `/webhooks/intake/contract` | Return the webhook payload contract as JSON documentation. |
| POST | `/webhooks/intake/fine` | Structured traffic fine notification. |
| POST | `/webhooks/intake/general` | Generic structured intake (fallback type). |
| POST | `/webhooks/intake/odometer` | Structured odometer reading from external gateway (WhatsApp photo → OCR → here). |
| POST | `/webhooks/intake/service` | Structured service request from driver. |
| POST | `/webhooks/intake/tires` | Structured tire change / check request. |

## MCP nástroje (`mcp/nexus_mcp.py`)

| Nástroj | Popis |
|---------|-------|
| `nexus_ping` | Ověří spojení a vrátí identitu/scopes API klíče. |
| `atlas_kpis` | Klíčové KPI holdingu (headcount, PHM, otevřené pojistky/pokuty/srážky, notifikace). |
| `fleet_vehicles` | Seznam vozidel (volitelně filtr status, např. ACTIVE). |
| `people` | Seznam osob (zaměstnanci). |
| `fortis_documents` | Ekonomické doklady (Fortis) — faktury/náklady, volitelně filtr. |
| `notifications` | Notifikace z Nexusu (volitelně filtr status, např. new). |
| `idoklad_invoices` | Faktury z iDokladu (kind=received|issued). |
| `create_notification` | Vytvoří in-app notifikaci v Nexusu (severity: info|warn|error). |
| `send_mail` | Odešle e-mail přes M365 (to = adresa nebo čárkou oddělené adresy). |
| `run_import` | Spustí import v Nexusu (name: fleet|fuel). |
| `idoklad_sync` | Stáhne faktury z iDokladu a zapíše je do Fortis (kind=received|issued). |

## Webové UI + veřejné routy (121)

| Method | Path | Auth | Popis |
|--------|------|------|-------|
| GET | `/` | public | root |
| GET | `/approvals` | cookie/JWT | approval_center |
| GET | `/atlas` | cookie/JWT | atlas_dashboard |
| GET | `/atlas/api/kpis` | cookie/JWT | atlas_kpis_api |
| GET | `/attendance` | cookie/JWT | attendance_console |
| POST | `/attendance/new` | cookie/JWT | create_period |
| GET | `/attendance/{period_id}` | cookie/JWT | period_detail |
| POST | `/attendance/{period_id}/approve` | cookie/JWT | approve_period |
| POST | `/attendance/{period_id}/export` | cookie/JWT | export_payroll |
| POST | `/attendance/{period_id}/lock` | cookie/JWT | lock_period |
| POST | `/attendance/{period_id}/save-row` | cookie/JWT | save_row |
| POST | `/attendance/{period_id}/submit` | cookie/JWT | submit_period |
| GET | `/auth/login` | public | login_page |
| POST | `/auth/login` | public | login_submit |
| GET | `/auth/logout` | public | logout |
| GET | `/calendar` | cookie/JWT | calendar_view |
| POST | `/calendar/event/new` | cookie/JWT | create_holding_event |
| GET | `/calendar/namedays/today` | cookie/JWT | today_namedays |
| GET | `/fleet` | cookie/JWT | fleet_board |
| GET | `/fleet/axigon` | cookie/JWT | axigon_overview |
| GET | `/fleet/axigon/contacts` | cookie/JWT | axigon_contacts |
| POST | `/fleet/axigon/contacts/{contact_id}/set-primary` | cookie/JWT | set_primary |
| POST | `/fleet/axigon/contacts/{contact_id}/toggle` | cookie/JWT | toggle_contact |
| GET | `/fleet/completion` | cookie/JWT | Přehled všech záznamů s chybějícími daty. |
| GET | `/fleet/completion/claim/{claim_id}` | cookie/JWT | completion_claim_form |
| POST | `/fleet/completion/claim/{claim_id}` | cookie/JWT | completion_claim_save |
| POST | `/fleet/deduction/new` | cookie/JWT | create_deduction |
| POST | `/fleet/deduction/{deduction_id}/approve` | cookie/JWT | approve_deduction |
| POST | `/fleet/deduction/{deduction_id}/export` | cookie/JWT | export_deduction |
| GET | `/fleet/deductions` | cookie/JWT | deduction_list |
| POST | `/fleet/deductions/export-batch` | cookie/JWT | export_deduction_batch |
| GET | `/fleet/driver/{person_id}` | cookie/JWT | driver_detail |
| POST | `/fleet/driver/{person_id}/odometer` | cookie/JWT | submit_odometer |
| GET | `/fleet/drivers` | cookie/JWT | driver_list |
| GET | `/fleet/phm` | cookie/JWT | phm_overview |
| GET | `/fleet/trips` | cookie/JWT | trip_list |
| POST | `/fleet/trips/new` | cookie/JWT | create_trip |
| POST | `/fleet/trips/{trip_id}/approve` | cookie/JWT | approve_trip |
| POST | `/fleet/trips/{trip_id}/ignore` | cookie/JWT | ignore_trip |
| GET | `/fleet/{vehicle_id}` | cookie/JWT | vehicle_detail |
| POST | `/fleet/{vehicle_id}/claim/new` | cookie/JWT | create_claim |
| POST | `/fleet/{vehicle_id}/driver` | cookie/JWT | assign_driver |
| POST | `/fleet/{vehicle_id}/edit` | cookie/JWT | edit_vehicle |
| POST | `/fleet/{vehicle_id}/event` | cookie/JWT | add_event |
| POST | `/fleet/{vehicle_id}/fine/new` | cookie/JWT | create_fine |
| GET | `/gov/api/messages` | public | List message notifications from DB (metadata only, no content). |
| POST | `/gov/api/messages/{message_id}/download` | public | On-demand download of a specific message (ZFO + attachments). |
| POST | `/gov/api/poll` | public | Manually trigger a poll of all active schránky. |
| GET | `/gov/api/schranky` | public | List all registered schránky with status. |
| GET | `/health` | public | health |
| GET | `/health/db` | public | health_db |
| GET | `/import` | cookie/JWT | import_center |
| GET | `/import/run/fleet` | public | run_fleet |
| GET | `/import/run/fuel` | public | run_fuel |
| GET | `/import/{batch_id}` | cookie/JWT | batch_detail |
| GET | `/import/{batch_id}/fleet` | cookie/JWT | staging_fleet |
| POST | `/import/{batch_id}/fleet/{row_id}/ignore` | cookie/JWT | ignore_fleet |
| POST | `/import/{batch_id}/fleet/{row_id}/link` | cookie/JWT | link_fleet |
| GET | `/import/{batch_id}/fuel` | cookie/JWT | staging_fuel |
| POST | `/import/{batch_id}/fuel/{row_id}/apply` | cookie/JWT | Promote reviewed/matched staging row → canonical FuelTransaction. |
| POST | `/import/{batch_id}/fuel/{row_id}/assign` | cookie/JWT | assign_fuel_row |
| POST | `/import/{batch_id}/fuel/{row_id}/ignore` | cookie/JWT | ignore_fuel_row |
| GET | `/import/{batch_id}/issues` | cookie/JWT | batch_issues |
| POST | `/import/{batch_id}/issues/{issue_id}/resolve` | cookie/JWT | resolve_issue |
| GET | `/import/{batch_id}/payroll` | cookie/JWT | staging_payroll |
| POST | `/import/{batch_id}/payroll/{row_id}/ignore` | cookie/JWT | ignore_payroll |
| POST | `/import/{batch_id}/payroll/{row_id}/link` | cookie/JWT | link_payroll |
| GET | `/import/{batch_id}/people` | cookie/JWT | staging_people |
| POST | `/import/{batch_id}/people/{row_id}/apply` | cookie/JWT | apply_person |
| POST | `/import/{batch_id}/people/{row_id}/link` | cookie/JWT | link_person |
| POST | `/import/{batch_id}/people/{row_id}/mark-new` | cookie/JWT | mark_new |
| GET | `/intake` | cookie/JWT | intake_list |
| GET | `/intake/new` | cookie/JWT | intake_new_form |
| POST | `/intake/new` | cookie/JWT | intake_create |
| GET | `/intake/{record_id}` | cookie/JWT | intake_detail |
| POST | `/intake/{record_id}/convert/claim` | cookie/JWT | convert_claim |
| POST | `/intake/{record_id}/convert/fine` | cookie/JWT | convert_fine |
| POST | `/intake/{record_id}/convert/odometer` | cookie/JWT | convert_odometer |
| POST | `/intake/{record_id}/ignore` | cookie/JWT | intake_ignore |
| POST | `/intake/{record_id}/review` | cookie/JWT | intake_review |
| GET | `/leave` | cookie/JWT | leave_list |
| POST | `/leave/new` | cookie/JWT | create_leave |
| POST | `/leave/{leave_id}/approve` | cookie/JWT | approve_leave |
| POST | `/leave/{leave_id}/reject` | cookie/JWT | reject_leave |
| GET | `/m365/api/calendar` | cookie/JWT | api_calendar |
| GET | `/m365/api/capabilities` | public | Machine-readable manifest of available M365 operations. |
| GET | `/m365/api/contacts` | cookie/JWT | api_contacts |
| GET | `/m365/api/files` | cookie/JWT | api_files |
| GET | `/m365/api/mail` | cookie/JWT | api_mail |
| POST | `/m365/api/mail/send` | cookie/JWT | api_send_mail |
| GET | `/m365/api/me` | cookie/JWT | api_me |
| GET | `/m365/calendar` | cookie/JWT | calendar_view |
| GET | `/m365/contacts` | cookie/JWT | contacts_list |
| GET | `/m365/files` | cookie/JWT | files_list |
| GET | `/m365/mail` | cookie/JWT | mail_inbox |
| GET | `/m365/mail/compose` | cookie/JWT | mail_compose |
| GET | `/m365/mail/search` | cookie/JWT | mail_search |
| POST | `/m365/mail/send` | cookie/JWT | mail_send |
| GET | `/m365/mail/{message_id}` | cookie/JWT | mail_detail |
| GET | `/notifications` | cookie/JWT | notification_center |
| POST | `/notifications/generate/all` | cookie/JWT | gen_all |
| POST | `/notifications/generate/compliance` | cookie/JWT | gen_compliance |
| POST | `/notifications/generate/deductions` | cookie/JWT | gen_deductions |
| POST | `/notifications/generate/fuel` | cookie/JWT | gen_fuel |
| POST | `/notifications/generate/odometer` | cookie/JWT | gen_odometer |
| POST | `/notifications/{notif_id}/acknowledge` | cookie/JWT | acknowledge |
| POST | `/notifications/{notif_id}/close` | cookie/JWT | close_notification |
| POST | `/notifications/{notif_id}/read` | cookie/JWT | mark_read |
| GET | `/people` | cookie/JWT | people_list |
| GET | `/people/merge` | cookie/JWT | merge_list |
| POST | `/people/merge/execute` | cookie/JWT | merge_execute |
| GET | `/people/merge/{id_a}/{id_b}` | cookie/JWT | merge_detail |
| POST | `/people/new` | cookie/JWT | person_create |
| GET | `/people/{person_id}` | cookie/JWT | person_detail |
| GET | `/people/{person_id}/contracts` | cookie/JWT | person_contracts |
| POST | `/people/{person_id}/contracts/new` | cookie/JWT | create_contract |
| POST | `/people/{person_id}/contracts/{contract_id}/deactivate` | cookie/JWT | deactivate_contract |
| POST | `/people/{person_id}/edit` | cookie/JWT | person_edit |
| POST | `/people/{person_id}/employment` | cookie/JWT | add_employment |
| POST | `/people/{person_id}/membership` | cookie/JWT | add_membership |
| POST | `/people/{person_id}/role` | cookie/JWT | add_role |

