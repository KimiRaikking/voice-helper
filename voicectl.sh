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
[ -f "$PYW" ] || PYW="$PY"             # 回退到 python.exe

# 单引号包住 PowerShell,防止 bash 展开 $_
PS_FIND='Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*voiced.py*" }'

case "${1:-}" in
  status)
    echo "=== 路径检查 ==="
    echo "repo: $DIR"
    [ -f "$DIR/.venv/Scripts/python.exe" ] && echo "venv python: 有" || echo "venv python: 缺(请先跑 python install.py)"
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
  fix)
    shift
    "$PY" "$DIR/add_fix.py" "$@"   # 加自动纠正规则: 错词 对词
    ;;
  download)
    shift
    "$PY" "$DIR/download_model.py" "$@"   # 走 voice.env 里的 VOICE_PROXY
    ;;
  clean)
    # 杀掉残留的 python.exe 下载/worker 进程(不动 pythonw 后台服务)+ 删锁
    powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force" 2>/dev/null
    rm -f "$DIR/.download.lock"
    echo "已清理残留下载进程 + 锁文件。"
    ;;
  doctor)
    code() { curl -s -m 8 -o /dev/null -w "%{http_code}" "$1" 2>/dev/null || echo 000; }
    eng=$(grep -E '^VOICE_ENGINE=' "$DIR/voice.env" 2>/dev/null | head -1 | cut -d= -f2)
    run=$(powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*voiced.py*' }) {'是'} else {'否'}" 2>/dev/null)
    ms="$HOME/.cache/modelscope/hub/models/iic"
    echo "===== 诊断结果 ====="
    [ -f "$DIR/.venv/Scripts/python.exe" ] && echo "1 venv环境 有" || echo "1 venv环境 无"
    echo "2 正在运行 ${run:-否}"
    echo "3 当前引擎 ${eng:-空}"
    # 检查真实权重文件(不只看目录是否存在,空目录=没下好)
    ls "$ms/SenseVoiceSmall/"*.pt >/dev/null 2>&1 && echo "4 中文模型SenseVoice 有" || echo "4 中文模型SenseVoice 无(空/缺)"
    ls "$ms"/*paraformer*/*.pt >/dev/null 2>&1 && echo "5 热词模型Paraformer 有" || echo "5 热词模型Paraformer 无(空/缺)"
    echo "6 连GitHub 返回 $(code https://github.com)"
    echo "7 连魔搭ModelScope 返回 $(code https://www.modelscope.cn)"
    echo "8 连抱抱脸HuggingFace 返回 $(code https://huggingface.co)"
    echo "===== 日志最后报错 ====="
    grep -iE "error|traceback|cannot|refused|timed out|timeout|connection|no module" \
      "$DIR/voiced.log" 2>/dev/null | tail -3 || echo "无"
    echo "(返回200=通,000=连不上)"
    ;;
  *)
    echo "用法: bash voicectl.sh {status|start|stop|restart|log|doctor|download [all]|hot <词...>|fix <错> <对>|clean}"
    ;;
esac
