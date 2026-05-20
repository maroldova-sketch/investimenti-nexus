# DKIM Enablement Runbook

End-to-end automation for enabling DKIM signing on the holding's M365 domains.

## Domains
- investimenti.cz
- vzc.cz
- logpack.cz
- zamek-citoliby.cz

## Why this is local (not container) work
DKIM management requires:
1. Interactive Global Admin login to Exchange Online (MFA-protected).
2. Cloudflare API token with `Zone.DNS:Edit` on the four zones.

The Claude Code container has neither. Run these scripts from your laptop.

## Prereqs (one-time)

```powershell
# PowerShell 7+
Install-Module -Name ExchangeOnlineManagement -Scope CurrentUser
```

```bash
# Python deps for the Cloudflare DNS step (already in requirements.txt: httpx)
pip install httpx
```

Create a Cloudflare token at https://dash.cloudflare.com/profile/api-tokens:
- Permissions: `Zone -> DNS -> Edit`
- Zone resources: include all four zones (or `Include All zones from an account`)

## Workflow

### 1. Rotate keys + capture CNAME targets

```powershell
pwsh ./enable_dkim.ps1 -Phase Rotate -Admin you@yourtenant.onmicrosoft.com
```

Output prints `Selector1CNAME` / `Selector2CNAME` for each domain. Format will be:

```
selector1-{domain-with-dashes}._domainkey.{tenant}.onmicrosoft.com
selector2-{domain-with-dashes}._domainkey.{tenant}.onmicrosoft.com
```

### 2. Publish CNAMEs to Cloudflare

```bash
export CF_API_TOKEN=cf_xxx
export ONMICROSOFT=vasezubnicentrum.onmicrosoft.com
python cloudflare_dkim_dns.py
```

The script is idempotent — re-running it only updates records that differ.

Verify propagation:

```bash
dig +short selector1._domainkey.investimenti.cz CNAME
dig +short selector2._domainkey.investimenti.cz CNAME
# (repeat for each domain)
```

### 3. Enable signing in Exchange Online

```powershell
pwsh ./enable_dkim.ps1 -Phase Enable -Admin you@yourtenant.onmicrosoft.com
```

If you get `CNAME records can't be found`, wait 5-15 min and retry. Microsoft
sometimes caches negative DNS responses longer than Cloudflare's TTL would
suggest.

### 4. Verify

```powershell
pwsh ./enable_dkim.ps1 -Phase Status -Admin you@yourtenant.onmicrosoft.com
```

Expected for each domain:
- `Enabled = True`
- `Status = Valid`

Send a test email from each domain to `check-auth@verifier.port25.com` or
`auth@dmarcian.com` and check that the report shows `dkim=pass`.

## Special case: investimenti.cz

CNAMEs are already in Cloudflare. You can skip Phase 1 for this domain and go
straight to Phase 2 — or let the rotate happen and update the (already correct)
CNAMEs idempotently via `cloudflare_dkim_dns.py`.
