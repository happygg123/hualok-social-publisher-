$ErrorActionPreference = 'Continue'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
$env:PYTHONUNBUFFERED = '1'
$logDir = 'publish_logs\manual'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ('tencent_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.log')
Write-Host "logging to $logFile"
python -u publish_batch.py --csv tasks\publish.test.tencent.csv --headed --timeout 1200 2>&1 | Tee-Object -FilePath $logFile
Write-Host "publish_exit=$LASTEXITCODE"
