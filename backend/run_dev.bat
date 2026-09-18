@echo off
cd /d "%~dp0"
echo ========================================================
echo   Starting CekInvest Backend with Project Virtualenv
echo ========================================================
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
pause
