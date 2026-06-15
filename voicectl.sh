#!/usr/bin/env bash
# Git Bash 控制脚本(Windows)。在 Git Bash 终端里运行:
#   bash voicectl.sh status            # 是否在跑 + 日志末尾
#   bash voicectl.sh start             # 手动启动(隐藏窗口)
#   bash voicectl.sh stop              # 停止
#   bash voicectl.sh restart           # 重启
#   bash voicectl.sh log               # 实时跟踪日志(Ctrl+C 退出)
#   bash voicectl.sh hot 时延 推理     # 加热词(Paraformer 引擎,即时生效)
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYW="$DIR/.venv/Scripts/pythonw.exe"   # 无控制台
PY="$DIR/.venv/Scripts/python.exe"     # 有控制台

# 单引号包住 PowerShell,防止 bash 展开 $_
PS_FIND='Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*voiced.py*" }'

case "${1:-}" in
  status)
    echo "=== voiced 是否在运行 ==="
    powershell -NoProfile -Command "\$p = $PS_FIND; if (\$p) { \$p | ForEach-Object { 'running, PID ' + \$_.ProcessId } } else { 'NOT running' }"
    echo "=== 日志末尾 ==="
    [ -f "$DIR/voiced.log" ] && tail -n 20 "$DIR/voiced.log" || echo "(暂无 voiced.log)"
    ;;
  stop)
    powershell -NoProfile -Command "$PS_FIND | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }"
    echo "voiced 已停止。"
    ;;
  start)
    ( cd "$DIR" && nohup "$PYW" voiced.py >/dev/null 2>&1 & )
    echo "voiced 已启动 — 托盘图标在右下角(点 ^ 展开)。"
    ;;
  restart)
    "$0" stop; sleep 1; "$0" start
    ;;
  log)
    tail -f "$DIR/voiced.log"
    ;;
  hot)
    shift
    "$PY" "$DIR/add_hotword.py" "$@"
    ;;
  *)
    echo "用法: bash voicectl.sh {status|start|stop|restart|log|hot <词...>}"
    ;;
esac
