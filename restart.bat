@echo off
setlocal
set "DIR=%~dp0"
call "%DIR%stop.bat"
timeout /t 1 /nobreak >/dev/null
set "PYW=%DIR%.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%DIR%.venv\Scripts\python.exe"
if not exist "%PYW%" (
  echo [ERROR] venv python not found under "%DIR%.venv\Scripts\"
  echo Run:  python install.py
  pause
  exit /b 1
)
start "" "%PYW%" "%DIR%voiced.py"
echo Restarted. Tray icon at bottom-right.
