@echo off
setlocal
set "DIR=%~dp0"
echo === paths ===
echo repo: "%DIR%"
if exist "%DIR%.venv\Scripts\pythonw.exe" (echo venv pythonw: FOUND) else (echo venv pythonw: MISSING - run: python install.py)
echo.
echo === running? ===
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*voiced.py*' }; if ($p) { $p | ForEach-Object { 'running, PID ' + $_.ProcessId } } else { 'NOT running' }"
echo.
echo === voiced.log (tail) ===
if exist "%DIR%voiced.log" (powershell -NoProfile -Command "Get-Content '%DIR%voiced.log' -Tail 20") else (echo no voiced.log yet)
