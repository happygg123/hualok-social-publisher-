$ErrorActionPreference = 'Continue'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
Write-Host 'Starting Douyin login. Please scan/confirm in the opened browser window.'
sau douyin login --account gavin --headed
Write-Host "douyin_login_exit=$LASTEXITCODE"
