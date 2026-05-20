<#
.SYNOPSIS
    Enable DKIM signing for all holding domains on Exchange Online.

.DESCRIPTION
    For each domain:
      1. Ensure DkimSigningConfig exists (create if missing).
      2. Rotate keys to generate fresh selector1/selector2 CNAME targets.
      3. Print the CNAME values you need in DNS.
      4. After you confirm DNS is propagated, flip Enabled=$true.

.PREREQUISITES
    - Exchange Online PowerShell V3:
        Install-Module -Name ExchangeOnlineManagement -Scope CurrentUser
    - Global Admin (or Exchange Admin) account with MFA.

.USAGE
    # Phase 1 — rotate keys and print CNAMEs:
    pwsh ./enable_dkim.ps1 -Phase Rotate -Admin you@tenant.onmicrosoft.com

    # ... add the CNAMEs to Cloudflare (manually or via cloudflare_dkim_dns.py),
    # wait ~5-15 min for propagation, then:

    # Phase 2 — enable signing:
    pwsh ./enable_dkim.ps1 -Phase Enable -Admin you@tenant.onmicrosoft.com
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Rotate", "Enable", "Status")]
    [string]$Phase,

    [Parameter(Mandatory = $true)]
    [string]$Admin,

    [string[]]$Domains = @(
        "investimenti.cz",
        "vzc.cz",
        "logpack.cz",
        "zamek-citoliby.cz"
    )
)

$ErrorActionPreference = "Stop"

Import-Module ExchangeOnlineManagement
Connect-ExchangeOnline -UserPrincipalName $Admin -ShowBanner:$false

function Show-Cname {
    param($cfg)
    [PSCustomObject]@{
        Domain          = $cfg.Domain
        Enabled         = $cfg.Enabled
        Status          = $cfg.Status
        Selector1CNAME  = $cfg.Selector1CNAME
        Selector2CNAME  = $cfg.Selector2CNAME
    }
}

switch ($Phase) {

    "Rotate" {
        foreach ($d in $Domains) {
            Write-Host "`n=== $d ===" -ForegroundColor Cyan
            $cfg = Get-DkimSigningConfig -Identity $d -ErrorAction SilentlyContinue
            if (-not $cfg) {
                Write-Host "  Config missing -> creating (disabled)..." -ForegroundColor Yellow
                New-DkimSigningConfig -DomainName $d -Enabled $false | Out-Null
            }
            Write-Host "  Rotating keys..." -ForegroundColor Yellow
            Rotate-DkimSigningConfig -Identity $d -KeySize 2048
            Start-Sleep -Seconds 2
            $cfg = Get-DkimSigningConfig -Identity $d
            Show-Cname $cfg
        }
        Write-Host "`nNow add the CNAMEs above to DNS for each domain:" -ForegroundColor Green
        Write-Host "  selector1._domainkey  CNAME  <Selector1CNAME>"
        Write-Host "  selector2._domainkey  CNAME  <Selector2CNAME>"
        Write-Host "Then re-run with -Phase Enable.`n"
    }

    "Enable" {
        foreach ($d in $Domains) {
            Write-Host "`n=== $d ===" -ForegroundColor Cyan
            try {
                Set-DkimSigningConfig -Identity $d -Enabled $true
                $cfg = Get-DkimSigningConfig -Identity $d
                Show-Cname $cfg
            }
            catch {
                Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
                Write-Host "  Most common cause: CNAMEs not yet visible to Microsoft. Wait 5-15 min and retry." -ForegroundColor Yellow
            }
        }
    }

    "Status" {
        foreach ($d in $Domains) {
            $cfg = Get-DkimSigningConfig -Identity $d -ErrorAction SilentlyContinue
            if ($cfg) { Show-Cname $cfg } else { Write-Host "$d : no config" }
        }
    }
}

Disconnect-ExchangeOnline -Confirm:$false
