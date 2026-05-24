$ErrorActionPreference = 'Continue'
Write-Host '=== python/powershell command lines ==='
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|powershell' } | Select-Object ProcessId,Name,CommandLine | Format-List
