# NEXUS People: intake, employee entry and protected documents

The module uses existing `Person`, `Entity`, `Employment`, `UserAccount` and
currently valid, scoped `RoleAssignment` records. It is off by default.
No production database, service, public route or mail account was changed.

## Implemented behavior

- HR opens one case per existing employment relationship at `/people/hr`.
  Concurrent HPP/DPP/DPČ relationships remain separate, with pinned legal
  employer, person and job context.
- The responsive employee form now has six steps: personal facts, contact and
  payroll inputs, conditional tax/family inputs, existing work/benefit evidence,
  documents, and review/submission. Server-owned fields and validation are
  versioned. Drafts save to SQL, never browser local/session storage. Stale
  writes return 409; retries cannot silently replace a newer version.
- An immutable submission contains answers, context, template version and the
  exact document manifest/hashes. Corrections create another revision. HR
  review and payroll receipt are separate, recorded decisions. Payroll receipt
  closes that case; later changes open a new case.
- HR selects requirements and evidence. Employees report existing equipment or
  benefits; they do not grant themselves a car, laptop, benefit or bonus.
  An uploaded document is not automatically marked legally verified.
- Existing Nexus accounts retain dated entity/division scope checks. Employees
  cannot review/accept their own submissions. The module does not overwrite
  `Person`, contracts or payroll calculations automatically.

## Employee invitation

HR selects an email already present on the existing person record and confirms
that it belongs to this employee. The address is not taken from the editable
intake draft. Creating an invitation returns a shareable link once; it does
**not** send a message. The UI supports copying a prepared message and native
mobile sharing. There is no WhatsApp Business API integration in this change.

The random 256-bit invitation ticket is stored only as a digest. It travels in
the URL fragment and is removed from the address bar by the entry page. A GET,
including a link preview, does not consume the ticket or send a code. The link
alone discloses no employee answers or identity. `/hr/entry` requests an
8-digit code through the configured TLS mail adapter after an explicit click.
Codes expire after ten minutes, allow five attempts each, and are single-use.
There is a 60-second resend cooldown, ten deliveries per invitation and twenty
failed verifications over its lifetime. SQL version counters arbitrate races.

An invitation lasts seven days. Verification creates a distinct, case-bound,
two-hour `HttpOnly; Secure; SameSite=Strict` cookie, scoped to `/hr`. It never
creates a Nexus account or JWT. The employee namespace exposes only the selected
case, draft, submit and document operations. HR/finance actions, case lists,
recipient management and access audits are not exposed there. An employee's
unrelated HR role never expands this portal session.

A new invitation supersedes the previous link/session. HR can revoke it. Contact
changes, expiry, invalid employment binding, inactive person/employer, terminated
employment and payroll receipt also invalidate access. Logout clears the session.
Resuming after session expiry uses the original invitation and a fresh code.
Mail failure returns an actionable error and invalidates the undelivered code;
no plaintext code or ticket is written to the audit log.

## Documents

- PDF, JPEG and PNG only; extension, declared MIME and file signature must agree.
  Each upload is streamed with an 8 MiB/30-second bound. There are at most twenty
  active and fifty lifetime document records per case. Proxies must additionally
  bound request concurrency, rates and slow connections.
- The ClamAV adapter uses **only a configured local Unix socket** and INSTREAM.
  A detection, timeout, unavailable scanner or ambiguous response rejects the
  upload. Files enter persistent storage only after an explicit clean scan.
  The scanner/version receipt is retained. Antivirus approval is not a guarantee
  of harmless content or legal correctness; no inline document rendering occurs.
- Accepted bytes are encrypted with Fernet/MultiFernet under a separate keyring
  before they are written. The private directory must exist outside the
  application tree with no group/other permissions. Server-generated UUID paths
  and mode 0600 replace user filenames. File and directory are flushed before
  committing their database reference.
- Downloads authenticate the case scope, decrypt and check the recorded digest,
  then return an attachment with no-store/nosniff headers. There are no public
  object URLs. Reads, uploads and withdrawals produce minimal access events.
- Withdrawal removes a file from the current draft, not from older snapshots.
  It is allowed only while editable and is refused while a requirement still
  references that document. A `document:<id>` evidence reference must belong to
  this same case. HR must explicitly review its content.
- A known transaction conflict removes its unreferenced ciphertext. An unknown
  database commit failure retains ciphertext for reconciliation, because deleting
  it could damage a commit that actually succeeded. There is no automatic orphan
  purge or invented retention period; operators must reconcile storage and DB
  backups and apply the approved retention policy.

## Runtime configuration

The internal workflow can be enabled independently. Invitations/uploads report
unavailable until their adapters are configured; there are no permissive
production test modes or plaintext storage fallbacks.

| Variable | Meaning |
|---|---|
| `NEXUS_HR_ENABLED=1` | Register the module after schema/signing-key checks. |
| `NEXUS_HR_PUBLIC_ORIGIN` | Exact HTTPS origin, no path/query/userinfo; the external proxy must preserve it. |
| `NEXUS_HR_SMTP_HOST`, `_PORT` | TLS-on-connect SMTP service; port defaults to 465. |
| `NEXUS_HR_SMTP_USER`, `_PASSWORD`, `_FROM` | Delivery credentials and sender; secrets come from deployment configuration. |
| `NEXUS_HR_DOCUMENT_ROOT` | Existing absolute private document directory outside the code tree. |
| `NEXUS_HR_DOCUMENT_KEYS` | Comma-separated Fernet keyring, newest first; separate from the Nexus signing key. |
| `NEXUS_HR_CLAMD_SOCKET` | Absolute path to the private ClamAV Unix socket. |

`_PORT`, `_USER`, `_PASSWORD` and `_FROM` above all use the complete
`NEXUS_HR_SMTP_` prefix. No real values or generated keys belong in Git.

The signing key must be nondefault and at least 32 characters. Keep document
keys available for restoration, separate from database/document backups. Adding
a new key first permits new writes while old files remain readable through older
keys. Removal of old keys requires a separately reviewed re-encryption procedure;
this patch does not silently rotate or discard them.

## Deployment boundary and staging runbook

1. Compare this branch against the actual running Nexus revision, not merely the
   GitHub main branch. Production parity is unverified. Use Python 3.11+ and the
   repository requirements; tests here used Python 3.12.
2. Back up and restore a staging copy. Never test on the checked-in `nexus.db` or
   a live payroll database. Inspect the explicit additive migration:

   ```sh
   python scripts/install_hr_schema.py --database-url sqlite:////absolute/staging/nexus.db
   ```

3. Apply it only to the selected staging database:

   ```sh
   python scripts/install_hr_schema.py --database-url sqlite:////absolute/staging/nexus.db --apply
   ```

   There are six HR tables in total. If the first three-table increment already
   exists, this adds only `hr_document`, `hr_invitation` and `hr_event`. Ordinary
   application startup does not migrate anything and refuses incompatible tables.
4. Provision the private directory, protected keyring, ClamAV/freshclam and TLS
   SMTP sender. ClamAV limits must cover the allowed file size and signature
   freshness must be monitored. Check a known test detection and a harmless
   document against the **actual** scanner, and verify real mail delivery in a
   controlled staging mailbox. This has not been done from this workspace.
5. Expose only `/hr/entry`, `/hr/api/…`, `/static/hr/app.js` and
   `/static/hr/style.css` through the external TLS proxy. Deny other routes,
   including `/people`, `/api/hr`, `/auth`, `/openapi.json`, `/import` and the
   internal health/admin surfaces. **Do not expose the whole Nexus port.**
   Preserve canonical Host and trusted forwarded HTTPS scheme; trust forwarded
   headers only from the actual proxy. Keep the upstream bound privately.
6. Apply proxy request/body/concurrency limits, particularly to code/verification
   and uploads. JSON is additionally bounded to 128 KiB by the module; binary
   documents are bounded by the upload handler. Test encoded traversal, forbidden
   paths, cookies, CSRF and case scope at the actual external origin.
7. Rehearse a real browser journey in staging: issue without sending, deliver to
   the designated test recipient, code verification, resume, upload, submit,
   return, resubmit, HR review, payroll receipt and revoked/expired access. Check
   a physical phone, backups/restoration and approved retention/deletion.
8. Confirm the real legal employer, recipient, minimum field set and responsible
   payroll owner before creating an actual employee case.

Rollback: disable `NEXUS_HR_ENABLED`, remove/disable the external proxy route and
restart through the normal deployment process. Retain HR tables, encrypted files
and keys. Do not perform a destructive database downgrade.

## Validation and known limits

```sh
python -m unittest discover -s tests -p 'test_hr*.py' -v
node --check frontend/static/hr/app.js
git diff --check
```

The suite contains 49 scenarios: 48 passed in this workspace and one actual Unix
socket transport test was skipped because the executor denies socket creation.
Controlled mail/scanner doubles test delivery failure, malware rejection, quotas,
expired/replayed codes, cross-case isolation, revocation, contact changes, SQL
races, encrypted files, immutable attachment manifests and keyring behavior.
A separate simulated transport test verifies INSTREAM bytes and truncated replies.
These tests do not prove actual SMTP deliverability or deployed antivirus health.

Browser QA covers case creation, preparing an invitation, the initial employee
entry page and the document step. The mobile content viewport is 375 px with
scrollWidth 375 px. External code consumption and document bytes were verified
through API tests; browser OTP entry/upload and a physical phone remain staging
checks. The synthetic preview uses an isolated in-memory database and controlled
adapters outside Git; those shortcuts are absent from production code.

The form remains a versioned intake subset, **not an exhaustive Czech legal
validator**. Annual tax settlement, detailed foreign-worker evidence, approved
insurance branches and the complete pilot minimum still need mapping. No tax
constants or legal calculations are introduced. Contract signatures, provider
cards, new benefit entitlements, KPI-linked rewards and payroll/ERP write adapters
remain separate work. Form completion or payroll receipt does not certify legal
work authorization, medical fitness, training or payroll calculation.

The weekly vendor watchdog is advisory. It proposes reviewed template/process
updates; it does not automatically change live fields, rights or payroll rules.

References: [OWASP file uploads](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html),
[OWASP token lifecycle](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html),
[ClamD protocol](https://docs.clamav.net/manual/Usage/ClamdProtocol.html),
[Fernet keyrings](https://cryptography.io/en/latest/fernet/),
[SQLAlchemy version counters](https://docs.sqlalchemy.org/en/20/orm/versioning.html).
