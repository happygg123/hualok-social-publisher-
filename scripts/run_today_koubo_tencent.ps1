$ErrorActionPreference = 'Continue'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
python -u publish_batch.py --csv tasks\publish.today.koubo.tencent.csv --headed --timeout 1200
Write-Host "publish_exit=$LASTEXITCODE"
