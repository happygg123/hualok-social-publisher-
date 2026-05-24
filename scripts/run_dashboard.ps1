$ErrorActionPreference = 'Stop'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
python publisher_dashboard.py
