# HR intake: first working increment

This adds an internal HR case workflow to the existing Nexus application at
`/people/hr`. It uses existing `Person`, `Entity`, `Employment`, `UserAccount`
and dated/scoped `RoleAssignment` records. It does not create another employee
directory or change the source of existing employment terms.

## What is implemented

- An HR operator selects an existing employment relationship and opens one
  `complete_existing` or `change` case. A concurrent relationship has a separate
  case. The legal employer and job context are pinned and visible.
- A five-step responsive form reads its field definitions and conditions from
  one server-owned template. It prefills existing facts, saves drafts to SQL,
  and restores them after a page refresh. No answers are stored in browser
  localStorage or sessionStorage. The UI distinguishes pending, successful and
  failed saves. A conflicting write returns 409 instead of overwriting data.
- Personal/contact/insurance/tax inputs, conditional children and months,
  existing equipment/benefits evidence and questions for HR. These are submitted
  facts and requests; they do not create legal entitlements or calculate payroll.
- Submission creates an immutable, numbered snapshot with a SHA-256 digest.
  A return for correction opens the draft again; resubmission creates a new
  snapshot. Historical snapshots and review decisions are retained.
- HR sets the evidence requirements and which block payroll handover. Verified
  evidence requires a reference; deferrals/exceptions require a reason. The
  current requirements are frozen in each review/acceptance decision.
- HR review and payroll receipt are separate transitions. Payroll receipt
  refers to the exact submitted revision, closes that case and does not imply
  that payroll has been calculated or regulatory reporting submitted. Later
  changes use a new case.
- API reads/writes enforce employment ownership or currently valid role scope.
  Entity and division scopes do not become global through `CurrentUser.roles`.
  CSRF protects mutations; own submissions cannot be self-reviewed/accepted.
  Create/action keys prevent duplicate operations. SQL version counters also
  reject simultaneous stale database writes. Lists omit submitted answers.

## Deliberate boundaries of this increment

This is an **internal authenticated workflow**, not an externally distributable
employee invitation service. Existing Nexus authentication is reused; there is
no public token endpoint or newly exposed internal port. The website prototype
is a separate, unchanged preview and does not become a real invitation.

Files are currently referenced in an existing approved protected repository.
Uploads, scanning, e-signatures, mail/WhatsApp delivery, provider-card operations,
benefit grants, KPI-linked rewards and payroll/ERP write connectors are not
implemented. Capability flags in `/api/hr/meta` explicitly report these gaps.
Health diagnoses and payment-card credentials are not requested.

The first form is a versioned **intake subset**. It is not an exhaustive Czech
legal/migration/tax schema. Existing prototype branches such as annual tax
settlement, foreign-worker evidence and complex insurance claims must be mapped
and validated before a real pilot is labelled complete. No tax constants or
legal calculations are implemented here. The vendor watchdog is advisory and
does not edit this version automatically.

The module intentionally does not write reviewed answers back to `Person` or
`EmploymentContract`: field ownership and payroll acceptance mappings still
need to be confirmed. Readiness for work, BOZP/medical compliance and adaptation
are not inferred from form completion or payroll receipt.

## Installation into a reviewed staging copy

The feature is off unless the process environment has `NEXUS_HR_ENABLED=1`.
Production has **not** been migrated, restarted or changed by this patch.

1. Review this branch against the actual running Nexus revision. The source
   checkout used for development was the GitHub `main` revision beginning
   `ddc570b`; a matching deployment on the host was not verified.
2. Use a backed-up staging database and the repository's pinned requirements.
   Never run tests against the checked-in `nexus.db` or a live payroll database.
3. Inspect the additive schema without making changes:

   ```sh
   python scripts/install_hr_schema.py --database-url sqlite:////absolute/staging/nexus.db
   ```

4. Apply the three new tables only after review:

   ```sh
   python scripts/install_hr_schema.py --database-url sqlite:////absolute/staging/nexus.db --apply
   ```

5. Enable the feature in staging with `NEXUS_HR_ENABLED=1`. Startup refuses a
   missing/incompatible HR schema or the default/short signing key. Reuse the
   actual protected Nexus signing configuration; never put credentials in Git.
6. Verify dated entity/division scopes with actual HR/payroll owners and the
   designated employment mapping. Verify access, backups/restore, retention,
   TLS and document repository controls for the target environment.
7. A genuine first employee case also needs confirmed legal employer, approved
   minimum intake fields, purpose/retention information, a working recipient
   access path and agreed handling of required documents. These are unresolved
   deployment inputs, not invented defaults.

Rollback: disable the feature flag and restart through the existing deployment
procedure. Keep the additive tables and their data; no destructive downgrade is
included. The schema installer never runs during ordinary application startup.

## Validation

```sh
python -m unittest discover -s tests -p test_hr_cases.py -v
node --check frontend/static/hr/app.js
git diff --check
```

Synthetic database tests cover authorization/expiry/division scopes, concurrent
relationships, CSRF/origin checks, idempotency, stale writers, removal of inactive
family data, conditional validation, immutable submissions, return/resubmission,
requirement evidence, precise payroll receipt, self-approval and retargeting.
The test database is in-memory with foreign keys enabled.

Browser QA used synthetic people and a separate in-memory preview: creation,
prefill, conditionally revealed children, monthly selections, persistence after
reload, submission, HR review and payroll receipt were exercised successfully.
The mobile wrapper was 390 px wide (375 px content viewport); document
scrollWidth was 375 px. This is browser-width QA, not a test on a physical phone.
Preview authentication shortcuts exist only in an untracked external QA harness;
they are not in this module or its production routes.

## Next integration increment

1. Confirm production source/deployment parity and field ownership mapping.
2. Complete the approved first-case schema and protected document intake.
3. Add recipient authentication and narrowly scoped invitation delivery.
4. Add a payroll adapter with revision receipts, retries and explicit field
   ownership; link operational ERP tasks only with an approved minimal payload.
5. Extend existing-benefit evidence to governed policies/entitlements and cards,
   and add KPI workflows in their independently reviewed stages.

Technical references: [FastAPI dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
and [SQLAlchemy version counters](https://docs.sqlalchemy.org/en/20/orm/versioning.html).
