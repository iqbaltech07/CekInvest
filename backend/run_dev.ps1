Set-Location -Path $PSScriptRoot
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Starting CekInvest Backend with Project Virtualenv" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
