@echo off
echo === voiced 是否在运行 ===
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*voiced.py*' }; if ($p) { $p | ForEach-Object { 'running, PID ' + $_.ProcessId } } else { 'NOT running' }"
echo.
echo === 日志末尾(看是否加载成功/有无报错) ===
if exist "%~dp0voiced.log" (powershell -NoProfile -Command "Get-Content '%~dp0voiced.log' -Tail 20") else (echo (暂无 voiced.log))
