$ErrorActionPreference = 'Continue'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
Write-Host 'Starting Tencent Channels login. Please scan/confirm in the opened browser window.'
sau tencent login --account gavin --headed
Write-Host "tencent_login_exit=$LASTEXITCODE"
