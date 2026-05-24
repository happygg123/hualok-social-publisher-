$ErrorActionPreference = 'Continue'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1

Write-Host '=== tencent ==='
sau tencent check --account gavin
Write-Host "tencent_exit=$LASTEXITCODE"

Write-Host '=== douyin ==='
sau douyin check --account gavin
Write-Host "douyin_exit=$LASTEXITCODE"

Write-Host '=== xiaohongshu ==='
sau xiaohongshu check --account gavin
Write-Host "xhs_exit=$LASTEXITCODE"
