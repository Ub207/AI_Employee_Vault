# Vault Sync Script — Platinum Tier
# Syncs vault to GitHub (private repo) for Cloud Agent access.
# Run: powershell -ExecutionPolicy Bypass -File scripts/sync_vault.ps1
# Or via Task Scheduler every 5 minutes.

param(
  [string]$Message = "Auto-sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
  [switch]$PullOnly
)

$VAULT = Split-Path $PSScriptRoot -Parent
Set-Location $VAULT

# Safety: never sync secrets
$gitignorePath = "$VAULT\.gitignore"
$protectedPatterns = @(".env", "*.token", ".whatsapp_session", "Secrets/", "*.key")
foreach ($p in $protectedPatterns) {
    if (-not (Select-String -Path $gitignorePath -Pattern ([regex]::Escape($p)) -Quiet -ErrorAction SilentlyContinue)) {
        Write-Warning "WARNING: '$p' may not be in .gitignore — check before syncing!"
    }
}

if ($PullOnly) {
    git pull --rebase origin main 2>&1
    Write-Output "[Vault Sync] Pulled latest from remote."
    exit 0
}

$status = git status --porcelain 2>&1
if (-not $status) {
    Write-Output "[Vault Sync] Nothing to sync — vault is clean."
    exit 0
}

git add `
    "Needs_Action/*.md" `
    "Tasks/*.md" `
    "Pending_Approval/**/*.md" `
    "Approved/*.md" `
    "Rejected/*.md" `
    "Done/*.md" `
    "Logs/*.md" `
    "In_Progress/**/*.md" `
    "Updates/*.md" `
    "Dashboard.md" `
    "CEO_Briefing.md" `
    "config.yaml" `
    "ecosystem.config.js" 2>&1

$changed = git diff --cached --name-only 2>&1
if (-not $changed) {
    Write-Output "[Vault Sync] No staged changes."
    exit 0
}

git commit -m $Message 2>&1
git push origin main 2>&1

Write-Output "[Vault Sync] Synced: $Message"
Write-Output "Files synced:`n$changed"
