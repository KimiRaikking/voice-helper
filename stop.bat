@echo off
REM 停止正在运行的 voiced
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*voiced.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo voiced 已停止。
