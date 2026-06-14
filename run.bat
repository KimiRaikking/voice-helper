@echo off
REM 手动启动(无窗口)。开机自启由 install.py 配置,不需要手动跑。
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0voiced.py"
