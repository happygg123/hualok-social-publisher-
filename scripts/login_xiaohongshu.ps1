$ErrorActionPreference = 'Continue'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
Write-Host 'Starting Xiaohongshu login. Please scan/confirm in the opened browser window.'
sau xiaohongshu login --account gavin --headed
Write-Host "xiaohongshu_login_exit=$LASTEXITCODE"
