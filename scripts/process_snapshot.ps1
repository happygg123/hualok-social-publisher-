$ErrorActionPreference = 'Continue'
Write-Host '=== process snapshot ==='
Get-Process | Where-Object { $_.ProcessName -match 'chrome|python|powershell' } | Select-Object ProcessName,Id,MainWindowTitle | Format-Table -AutoSize
