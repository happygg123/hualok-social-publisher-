$ErrorActionPreference = 'Stop'
Set-Location 'D:\workspace\gavin-social-publisher'
. .\.venv\Scripts\Activate.ps1
python publisher_worker.py --interval 30 --headed --timeout 1800
