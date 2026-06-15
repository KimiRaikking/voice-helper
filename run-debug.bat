@echo off
setlocal
set "DIR=%~dp0"
set "PY=%DIR%.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] venv python not found: "%PY%"
  echo Run:  python install.py
  pause
  exit /b 1
)
echo Running in foreground (Ctrl+C to quit)...
"%PY%" "%DIR%voiced.py"
pause
