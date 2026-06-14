"""Cross-platform primitives for the voice dictation tool.

Isolates the OS-specific bits (clipboard, paste keystroke, sound cues, notifications)
so voiced.py stays platform-agnostic. Supports macOS and Windows (Linux best-effort).
"""
import subprocess
import sys
import time

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

# Right Option on mac / Right Alt on Windows both work as a push-to-talk key.
DEFAULT_HOTKEY = "alt_r"

# Modifier for the paste shortcut: Cmd on mac, Ctrl elsewhere.
from pynput.keyboard import Controller, Key  # noqa: E402

_kbd = Controller()
PASTE_MOD = Key.cmd if IS_MAC else Key.ctrl


def copy_to_clipboard(text: str) -> None:
    """Put text on the system clipboard (cross-platform via pyperclip)."""
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        # Fallbacks if pyperclip is unavailable.
        if IS_MAC:
            subprocess.run("pbcopy", input=text.encode("utf-8"), check=False)
        elif IS_WIN:
            subprocess.run("clip", input=text.encode("utf-16-le"), shell=True, check=False)


def paste() -> None:
    """Simulate the paste shortcut (Cmd/Ctrl + V) into the focused field."""
    with _kbd.pressed(PASTE_MOD):
        _kbd.press("v")
        _kbd.release("v")


# --- Sound cues (optional; off by default) -------------------------------------
_MAC_SOUNDS = {"rec": "Pop", "proc": "Tink", "done": "Glass", "err": "Basso"}
# Windows: (frequency Hz, duration ms) tones via winsound.Beep
_WIN_BEEPS = {"rec": (880, 80), "proc": (660, 70), "done": (1040, 90), "err": (300, 160)}


def play_cue(name: str) -> None:
    try:
        if IS_MAC:
            snd = _MAC_SOUNDS.get(name)
            if snd:
                subprocess.Popen(["afplay", f"/System/Library/Sounds/{snd}.aiff"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif IS_WIN:
            import winsound
            freq, dur = _WIN_BEEPS.get(name, (0, 0))
            if freq:
                winsound.Beep(freq, dur)
    except Exception:
        pass


def notify(text: str, title: str = "🎙️ 语音输入") -> None:
    """Best-effort desktop notification with the recognized text."""
    body = text.replace('"', "'")
    if len(body) > 110:
        body = body[:110] + "…"
    try:
        if IS_MAC:
            subprocess.Popen(["osascript", "-e",
                              f'display notification "{body}" with title "{title}"'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif IS_WIN:
            # Lightweight PowerShell balloon-free toast via BurntToast is overkill;
            # use a simple message via msg if available, else skip silently.
            ps = (
                "powershell -NoProfile -WindowStyle Hidden -Command "
                "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
                f"$n=New-Object System.Windows.Forms.NotifyIcon;$n.Icon=[System.Drawing.SystemIcons]::Information;"
                f"$n.Visible=$true;$n.ShowBalloonTip(3000,'{title}','{body}',[System.Windows.Forms.ToolTipIcon]::Info);"
                "Start-Sleep -Milliseconds 3500;$n.Dispose()"
            )
            subprocess.Popen(ps, shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def set_accessory_app() -> None:
    """On macOS, run as a menu-bar accessory (no Dock icon). No-op elsewhere."""
    if IS_MAC:
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
            NSApplication.sharedApplication().setActivationPolicy_(
                NSApplicationActivationPolicyAccessory)
        except Exception:
            pass


# Small convenience used by the tray flash timing.
def now_ts() -> float:
    return time.time()
