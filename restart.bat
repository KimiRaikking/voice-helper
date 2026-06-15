@echo off
REM 重启 voiced(停止 + 重新启动)
call "%~dp0stop.bat"
timeout /t 1 /nobreak >/dev/null
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0voiced.py"
echo voiced 已重启 — 托盘图标在右下角(点 ^ 展开)。
