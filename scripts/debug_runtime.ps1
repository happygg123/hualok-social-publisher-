$ErrorActionPreference = 'Continue'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
Write-Host '=== process snapshot ==='
Get-Process | Where-Object { $_.ProcessName -match 'chrome|python|powershell' } | Select-Object ProcessName,Id,MainWindowTitle | Format-Table -AutoSize
Write-Host '=== tencent check ==='
sau tencent check --account gavin
Write-Host "tencent_exit=$LASTEXITCODE"
