$ErrorActionPreference = 'Continue'
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*gavin-social-publisher*publish_batch.py*' -or
    $_.CommandLine -like '*gavin-social-publisher*.venv*Scripts*sau.exe*tencent upload-video*'
} | ForEach-Object {
    Write-Host "Killing $($_.ProcessId): $($_.CommandLine)"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
