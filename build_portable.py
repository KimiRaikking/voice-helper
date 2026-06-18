#!/usr/bin/env python3
r"""打包「免安装绿色版」(Windows)。

在一台**已经装好并能正常用**的 Windows 机器上运行(模型已下好、代理已配)。
产物:dist\voice-helper-portable\  以及同名 .zip —— 内含:
  - 内嵌 Python(embeddable,无需系统装 Python)
  - 全部依赖(faster-whisper / funasr / sensevoice 等)
  - 已下好的模型(同事无需联网/代理)
  - 一键启动器(启动语音输入.bat / 停止.bat / 卸载.bat)

同事拿到 zip 后:解压到**纯英文路径**(如 C:\voice-helper),双击「启动语音输入.bat」即可,
不装 Python、不用 Git、不下模型、不碰代理。

依赖**复用本机 .venv 里已装好的包**(本地拷贝,不走 PyPI),模型也是本地拷贝,所以打包
**几乎不需要网络**——只有一个 ~10MB 的内嵌 Python 要从 python.org 下(封了就手动下一次
`python-X.Y.Z-embed-amd64.zip` 放到脚本目录即可)。

    用本机 venv 的 Python 跑(保证版本与已装包一致):
    .venv\Scripts\python build_portable.py
"""
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist" / "voice-helper-portable"
PYDIR = DIST / "python"
VENV_SP = HERE / ".venv" / "Lib" / "site-packages"  # 已装好的包(复用,免联网)

# 内嵌 Python 版本必须与本机 .venv 的 Python major.minor 一致(编译扩展 ABI)。
# 用运行本脚本的解释器版本自动匹配;可用 PORTABLE_PY 覆盖完整版本号。
_EMBED_MICRO = {"3.10": "3.10.11", "3.11": "3.11.9", "3.12": "3.12.7", "3.13": "3.13.1"}
_MM = f"{sys.version_info.major}.{sys.version_info.minor}"
PYTAG = os.environ.get("PORTABLE_PY", _EMBED_MICRO.get(_MM, _MM + ".0"))
EMBED_URL = f"https://www.python.org/ftp/python/{PYTAG}/python-{PYTAG}-embed-amd64.zip"

# 要随程序打包的文件(代码 + 启动脚本 + 配置样例)
FILES = [
    "voiced.py", "vplatform.py", "tray.py", "add_hotword.py", "add_fix.py",
    "voice.env.example", "hotwords.txt.example", "corrections.txt.example",
]


def sh(cmd):
    print("  $", " ".join(map(str, cmd)), flush=True)
    subprocess.check_call([str(c) for c in cmd])


def fetch(url, dest):
    print(f"• 下载 {url}")
    urllib.request.urlretrieve(url, dest)


def _local_embed_zip():
    """允许用本地已下好的内嵌 Python zip(免联网)。放脚本目录即可,或用
    PORTABLE_EMBED_ZIP 指定。"""
    env = os.environ.get("PORTABLE_EMBED_ZIP")
    if env and Path(env).exists():
        return Path(env)
    for p in HERE.glob(f"python-{PYTAG}-embed-amd64.zip"):
        return p
    for p in HERE.glob("python-*-embed-amd64.zip"):
        return p
    return None


def stage_python():
    PYDIR.mkdir(parents=True, exist_ok=True)
    local = _local_embed_zip()
    z = DIST / "py-embed.zip"
    if local:
        print(f"• 用本地内嵌 Python: {local}")
        shutil.copy2(local, z)
    else:
        fetch(EMBED_URL, z)  # ~10MB,python.org;封了就手动下一次放脚本目录
    with zipfile.ZipFile(z) as f:
        f.extractall(PYDIR)
    z.unlink()
    # 打开 site + 让 Lib\site-packages 生效(不需要 pip)
    for pth in PYDIR.glob("python*._pth"):
        txt = pth.read_text(encoding="utf-8")
        txt = txt.replace("#import site", "import site")
        if "Lib\\site-packages" not in txt:
            txt += "\nLib\\site-packages\n"
        pth.write_text(txt, encoding="utf-8")


def copy_site_packages():
    """复用本机 .venv 里已装好的包(本地拷贝,完全不走 PyPI / 代理)。"""
    if not VENV_SP.is_dir():
        sys.exit(f"找不到已装好的包目录: {VENV_SP}\n请在已 install.py 装好的机器上运行,"
                 f"且用 .venv 的 Python 跑: .venv\\Scripts\\python build_portable.py")
    dst = PYDIR / "Lib" / "site-packages"
    dst.mkdir(parents=True, exist_ok=True)
    print(f"• 复制依赖 {VENV_SP} -> {dst}(可能要一两分钟)")
    for name in os.listdir(VENV_SP):
        s = VENV_SP / name
        d = dst / name
        if s.is_dir():
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)


def copy_code():
    for name in FILES:
        src = HERE / name
        if src.exists():
            shutil.copy2(src, DIST / name)
    # 默认配置:SenseVoice(同事最稳的引擎)
    (DIST / "voice.env").write_text(
        "VOICE_ENGINE=sensevoice\nVOICE_KEY=alt_r\nVOICE_LANG=zh\n", encoding="utf-8")
    for seed in ("hotwords.txt", "corrections.txt"):
        ex = DIST / f"{seed}.example"
        if ex.exists():
            shutil.copy2(ex, DIST / seed)


def copy_models():
    """把已下好的 SenseVoice 模型放进 bundle\\models\\，同事无需联网。
    优先用 voice.env 实际配置的路径(fixpath 后在 <盘符>\\voicehelper-models)。"""
    target = DIST / "models"
    target.mkdir(exist_ok=True)

    sources = []
    # 1) 读 voiced 解析出的真实模型路径(最准,认 fixpath / 本地目录 / 缓存)
    try:
        sys.path.insert(0, str(HERE))
        import voiced
        if voiced.SENSEVOICE_MODEL and os.path.isdir(voiced.SENSEVOICE_MODEL):
            sources.append(Path(voiced.SENSEVOICE_MODEL))
    except Exception as e:
        print(f"  (读 voice.env 模型路径失败,改用目录搜索: {e})")
    # 2) 兜底:常见位置搜 SenseVoiceSmall(含 fixpath 的两个盘)
    drives = {os.environ.get("SystemDrive", "C:"), os.path.splitdrive(str(HERE))[0] or "C:"}
    bases = [HERE / "models", Path.home() / ".cache/modelscope/hub/models/iic"]
    bases += [Path(d + os.sep + "voicehelper-models") for d in drives if d]
    for base in bases:
        if base.is_dir():
            for name in os.listdir(base):
                if "SenseVoiceSmall" in name and (base / name).is_dir():
                    sources.append(base / name)  # 只认目录,跳过 .rar/.zip 等压缩包

    print(f"  目标: {target}")
    print(f"  候选源({len(sources)} 个):")
    for s in sources:
        print(f"    - {s}  存在={os.path.isdir(str(s))}")

    def _is_model_dir(p):
        try:
            return p.is_dir() and any(f.endswith(".pt") for f in os.listdir(p))
        except OSError:
            return False

    seen, copied = set(), 0
    for src in sources:
        src = Path(str(src))
        if not _is_model_dir(src):  # 必须是含 model.pt 的目录(跳过 .rar/空目录)
            continue
        name = src.name
        d = target / name
        if name in seen or d.exists():
            continue
        seen.add(name)
        try:
            print(f"• 复制模型 {src} -> {d}", flush=True)
            shutil.copytree(src, d)
            copied += 1
        except Exception as e:
            print(f"  ⚠ 复制失败({type(e).__name__}: {e}),跳过这个源", flush=True)

    if copied == 0:
        print("⚠ 没复制到任何模型!可手动把 SenseVoiceSmall 目录拷到 "
              f"{target}\\  下再继续(然后注释掉 main 里的 copy_models 重跑,或直接打包)。")


_LAUNCH = r'''@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动语音输入...
REM 开机自启:在“启动”文件夹放一个隐藏启动项(指向本绿色版)
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\voice-helper.vbs"
> "%VBS%" echo Set s = CreateObject("Wscript.Shell")
>> "%VBS%" echo s.Run """%~dp0python\pythonw.exe"" ""%~dp0voiced.py""", 0, False
REM 立即启动一份
start "" "%~dp0python\pythonw.exe" "%~dp0voiced.py"
echo 已启动!右下角托盘有 🎤 图标。按住右 Alt 键说话,松开即出字。
echo (已设为开机自启;关闭本窗口不影响运行)
timeout /t 5 >nul
'''

_STOP = r"""@echo off
chcp 65001 >nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*voiced.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo 已停止语音输入。
timeout /t 3 >nul
"""

_UNINSTALL = r"""@echo off
chcp 65001 >nul
call "%~dp0停止.bat"
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\voice-helper.vbs" 2>nul
echo 已卸载(已停止 + 取消开机自启)。删除本文件夹即可彻底清除。
timeout /t 4 >nul
"""

# 调试:用控制台 python.exe 跑,直接显示报错(排查“双击没图标”用这个)
_DEBUG = r"""@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 调试模式(前台运行,显示报错)。Ctrl+C 退出。
"%~dp0python\python.exe" voiced.py
echo.
echo ===== voiced 已退出。上面如果有 Traceback / Error 就是原因 =====
pause
"""


def write_launchers():
    (DIST / "启动语音输入.bat").write_text(_LAUNCH, encoding="utf-8")
    (DIST / "停止.bat").write_text(_STOP, encoding="utf-8")
    (DIST / "卸载.bat").write_text(_UNINSTALL, encoding="utf-8")
    (DIST / "调试启动.bat").write_text(_DEBUG, encoding="utf-8")
    (DIST / "使用说明.txt").write_text(
        "Voice Helper 绿色版(免安装)\n\n"
        "1. 把本文件夹解压到纯英文路径,如 C:\\voice-helper(不要放中文目录!)\n"
        "2. 双击「启动语音输入.bat」\n"
        "3. 右下角托盘出现 🎤 图标后,在任意输入框按住【右 Alt 键】说话,松开即出字\n"
        "4. 已设为开机自启;想停用双击「停止.bat」,想彻底删除双击「卸载.bat」再删文件夹\n",
        encoding="utf-8")


def zip_bundle():
    zpath = HERE / "dist" / "voice-helper-portable.zip"
    print(f"• 打包 {zpath}")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in DIST.rglob("*"):
            zf.write(p, p.relative_to(DIST.parent))
    print(f"✅ 完成: {zpath}  ({zpath.stat().st_size/1e6:.0f} MB)")


def main():
    if os.name != "nt":
        sys.exit("请在 Windows 上运行此打包脚本。")
    print(f"Python: {sys.version.split()[0]}  内嵌版本: {PYTAG}")
    print(f"已装包目录: {VENV_SP}  存在={VENV_SP.is_dir()}")
    steps = [
        ("清理输出目录", lambda: (shutil.rmtree(DIST) if DIST.exists() else None, DIST.mkdir(parents=True))),
        ("准备内嵌 Python", stage_python),
        ("复制依赖(site-packages)", copy_site_packages),
        ("复制代码 + 写配置", copy_code),
        ("复制模型", copy_models),
        ("写一键启动器", write_launchers),
        ("打包 zip", zip_bundle),
    ]
    for i, (name, fn) in enumerate(steps, 1):
        print(f"\n===> 步骤 {i}/{len(steps)}: {name}", flush=True)
        try:
            fn()
        except Exception as e:
            import traceback
            print(f"❌ 步骤「{name}」失败: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            sys.exit(1)
    print("\n把 dist\\voice-helper-portable.zip 发给同事即可。")


if __name__ == "__main__":
    main()
