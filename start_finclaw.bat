@echo off
setlocal

echo [FINCLAW] Starting backend and frontend...

set ROOT=%~dp0
set BACKEND=%ROOT%backend
set FRONTEND=%ROOT%ArmorClawFrontend-main\Armorclaw frontend

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
  echo [FINCLAW] Backend virtual environment not found at "%BACKEND%\.venv".
  echo Create it first and install requirements.
  exit /b 1
)

if not exist "%BACKEND%\.env" (
  echo [FINCLAW] backend\.env not found. Copying from .env.example...
  copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
)

start "FINCLAW Backend" cmd /k "pushd "%BACKEND%" && .venv\Scripts\python.exe seed.py && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "FINCLAW Frontend" cmd /k "pushd "%FRONTEND%" && "%BACKEND%\.venv\Scripts\python.exe" -m http.server 3000"

echo.
echo [FINCLAW] Launch initiated.
echo Frontend: http://127.0.0.1:3000
echo Backend:  http://127.0.0.1:8000
echo Docs:     http://127.0.0.1:8000/docs

endlocal
