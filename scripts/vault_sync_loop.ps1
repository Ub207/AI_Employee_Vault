# Vault Sync Loop - Platinum Tier (Local Windows)
# Calls sync_vault.ps1 as a subprocess every 60 seconds.
# Uses subprocess (not dot-source) so 'exit' in sync_vault.ps1 does not kill this loop.

$VAULT = Split-Path $PSScriptRoot -Parent
$SYNC_SCRIPT = Join-Path $PSScriptRoot "sync_vault.ps1"
$Interval = 60

Write-Output "[Vault Sync Loop] Started - interval: ${Interval}s - vault: $VAULT"

while ($true) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "[$ts] Running vault sync..."

    & powershell.exe -ExecutionPolicy Bypass -File $SYNC_SCRIPT

    $ts2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "[$ts2] Sync complete. Sleeping ${Interval}s..."
    Start-Sleep -Seconds $Interval
}
