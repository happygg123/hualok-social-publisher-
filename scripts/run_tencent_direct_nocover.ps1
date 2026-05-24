$ErrorActionPreference = 'Continue'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
$logDir = 'publish_logs\manual'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ('sau_tencent_direct_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.log')
Write-Host "logging to $logFile"
sau tencent upload-video `
  --account gavin `
  --file 'D:\workspace\gavin-social-publisher\test_assets\gavin_koubo_small.mp4' `
  --title 'China sourcing service test' `
  --desc 'Gavin sourcing service for hardware tools building materials supplier matching and order follow up.' `
  --tags 'China sourcing,supply chain,factory sourcing' `
  --short-title 'Sourcing' `
  --headed 2>&1 | Tee-Object -FilePath $logFile
Write-Host "sau_exit=$LASTEXITCODE"
