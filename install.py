#!/usr/bin/env python3
"""Cross-platform installer for the Voice push-to-talk dictation tool.

    python install.py                 # venv + deps + autostart
    python install.py --no-sensevoice # skip the heavy SenseVoice/torch deps
    python install.py --no-autostart  # don't configure login autostart
    python install.py --no-start      # configure but don't launch now

Works on macOS (Apple Silicon) and Windows (CPU). Linux is best-effort.
Run it with any Python 3.10+: `python install.py` (it builds its own .venv).
"""
import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path

HERE = Path(__file__).resolve().parent
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
VENV = HERE / ".venv"
VPY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")
VPYW = VENV / "Scripts/pythonw.exe"  # Windows: no-console launcher


def run(cmd):
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.check_call([str(c) for c in cmd])


def create_venv():
    if VPY.exists():
        print("• venv already exists — reusing")
        return
    print("• creating virtual environment (.venv) ...")
    venv.EnvBuilder(with_pip=True).create(str(VENV))


def install_deps(with_sensevoice: bool):
    run([VPY, "-m", "pip", "install", "-q", "--upgrade", "pip"])
    reqs = [HERE / "requirements-common.txt",
            HERE / ("requirements-macos.txt" if IS_MAC else "requirements-windows.txt")]
    if with_sensevoice:
        reqs.append(HERE / "requirements-sensevoice.txt")
    for r in reqs:
        print(f"• installing {r.name} ...")
        run([VPY, "-m", "pip", "install", "-r", str(r)])


def ensure_config():
    cfg = HERE / "voice.env"
    ex = HERE / "voice.env.example"
    if not cfg.exists() and ex.exists():
        cfg.write_text(ex.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"• wrote {cfg.name} (edit it to change engine/hotkey/language)")
    else:
        print("• voice.env present — leaving your config untouched")


# --- autostart -----------------------------------------------------------------
_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.voicehelper.dictation</string>
  <key>ProgramArguments</key><array>
    <string>{py}</string><string>{script}</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict></plist>
"""


def autostart_mac(start_now: bool):
    plist = Path.home() / "Library/LaunchAgents/com.voicehelper.dictation.plist"
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(_PLIST.format(py=VPY, script=HERE / "voiced.py", log=HERE / "voiced.log"))
    subprocess.run(["launchctl", "unload", str(plist)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if start_now:
        subprocess.run(["launchctl", "load", str(plist)])
    print(f"• autostart installed: {plist}")
    print("  ⚠️ macOS 还需在『系统设置→隐私与安全性』给这个 python 授予")
    print(f"     输入监控 + 辅助功能 + 麦克风:\n     {VPY.resolve()}")


def autostart_windows(start_now: bool):
    startup = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"
    startup.mkdir(parents=True, exist_ok=True)
    pyw = VPYW if VPYW.exists() else VPY
    target = HERE / "voiced.py"
    vbs = startup / "voice-helper.vbs"
    # window style 0 = hidden, so no console window at login
    vbs.write_text(
        'Set s = CreateObject("Wscript.Shell")\r\n'
        f's.Run """{pyw}"" ""{target}""", 0, False\r\n',
        encoding="utf-8",
    )
    print(f"• autostart installed: {vbs}")
    if start_now:
        subprocess.Popen([str(pyw), str(target)])


def configure_autostart(start_now: bool):
    if IS_MAC:
        autostart_mac(start_now)
    elif IS_WIN:
        autostart_windows(start_now)
    else:
        print("• Linux: autostart not auto-configured; run with run-debug equivalent or add to your DE.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-sensevoice", action="store_true", help="skip SenseVoice/torch deps")
    ap.add_argument("--no-autostart", action="store_true", help="don't configure login autostart")
    ap.add_argument("--no-start", action="store_true", help="configure but don't launch now")
    args = ap.parse_args()

    plat = "macOS" if IS_MAC else "Windows" if IS_WIN else "Linux"
    print(f"=== Voice 安装器 ({plat}) ===")
    create_venv()
    install_deps(with_sensevoice=not args.no_sensevoice)
    ensure_config()
    if not args.no_autostart:
        configure_autostart(start_now=not args.no_start)

    print("\n✅ 完成!")
    print("• 配置文件: voice.env(改引擎/热键/语言后,重启即可)")
    print("• 首次说话时会下载模型(SenseVoice 从 ModelScope;Whisper 从 HuggingFace)")
    print("• 按住热键(默认右 Option / 右 Alt)说话 → 松开 → 自动插入光标处")
    if IS_WIN:
        print("• 手动启动: 双击 run.bat;调试看报错: run-debug.bat")


if __name__ == "__main__":
    main()
