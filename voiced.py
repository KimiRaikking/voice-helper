#!/usr/bin/env python3
"""Always-on push-to-talk voice dictation with a status tray icon. Cross-platform.

Hold the hotkey (default: Right Option / Right Alt) -> speak -> release. The speech
is transcribed locally and pasted into the focused field via clipboard + paste key.
A tray/menu-bar icon shows the live state:

    🎤 ready   🔴 recording   ⏳ transcribing   ✅ done   ⚠️ error

Engines (VOICE_ENGINE):
    whisper      Whisper. macOS->mlx-whisper (GPU); Windows/Linux->faster-whisper (CPU).
    sensevoice   FunASR SenseVoice (Chinese-optimized), cross-platform.

Env:
    VOICE_ENGINE   "whisper" (default) | "sensevoice"
    VOICE_KEY      hotkey: alt_r (default), alt_l, ctrl_r, cmd_r, f5, ...
    VOICE_LANG     force language code (e.g. zh / en). Default: auto-detect.
    WHISPER_MODEL  whisper model. mlx repo on mac, faster-whisper size/path on win.
    SENSEVOICE_MODEL  SenseVoice model (default: iic/SenseVoiceSmall)
    VOICE_PROMPT   Whisper initial_prompt (bias toward your vocabulary)
    VOICE_NO_PASTE if set, only copy to clipboard (don't auto-paste)
    VOICE_SOUND    if set, also play sound cues on state changes
    VOICE_NOTIFY   if "1", also post a desktop notification with the text
"""
import os
import queue
import sys
import threading
import time

import numpy as np
import sounddevice as sd
from pynput import keyboard
from pynput.keyboard import Key

import vplatform as vp
from tray import create_tray


def _load_env_file():
    """Load KEY=VALUE config from voice.env next to this script (does not override
    real environment variables, so per-platform autostart can still win)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice.env")
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass


_load_env_file()

SAMPLE_RATE = 16000
ENGINE = os.environ.get("VOICE_ENGINE", "whisper").lower()  # "whisper" | "sensevoice"
WHISPER_MODEL_ENV = os.environ.get("WHISPER_MODEL") or None
SENSEVOICE_MODEL = os.environ.get("SENSEVOICE_MODEL", "iic/SenseVoiceSmall")
LANG = os.environ.get("VOICE_LANG") or None
PROMPT = os.environ.get("VOICE_PROMPT") or None
AUTO_PASTE = "VOICE_NO_PASTE" not in os.environ
SOUND = "VOICE_SOUND" in os.environ
NOTIFY = os.environ.get("VOICE_NOTIFY") == "1"
MIN_SECONDS = 0.3
FLASH_SECONDS = 1.2  # how long done/err stays before reverting to idle

KEY_MAP = {
    "alt_r": Key.alt_r, "alt_l": Key.alt_l, "alt": Key.alt,
    "ctrl_r": Key.ctrl_r, "ctrl_l": Key.ctrl_l,
    "cmd_r": Key.cmd_r, "cmd_l": Key.cmd_l,
    "shift_r": Key.shift_r, "shift_l": Key.shift_l,
    "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
}
KEY_NAME = os.environ.get("VOICE_KEY", vp.DEFAULT_HOTKEY)
HOTKEY = KEY_MAP.get(KEY_NAME, Key.alt_r)

_mlx = None
_fw_model = None
_whisper_backend = None  # "mlx" | "faster"
_sv_model = None         # lazily-loaded SenseVoice (funasr) model

# Whisper sometimes emits Traditional Chinese; force Simplified (no effect on English).
try:
    from opencc import OpenCC
    _cc = OpenCC("t2s")
except Exception:
    _cc = None


def _to_simplified(text: str) -> str:
    if _cc and text:
        try:
            return _cc.convert(text)
        except Exception:
            return text
    return text


# --- shared UI state -----------------------------------------------------------
class State:
    """Thread-safe state shared with the tray poller."""
    def __init__(self):
        self.lock = threading.Lock()
        self.name = "idle"
        self.ts = 0.0
        self.last_text = ""

    def set(self, name: str, text: str | None = None):
        with self.lock:
            self.name = name
            self.ts = vp.now_ts()
            if text is not None:
                self.last_text = text
        if SOUND:
            vp.play_cue(name)

    def snapshot(self):
        with self.lock:
            return self.name, self.ts, self.last_text

    def display(self):
        """Return (icon_key, last_text), auto-reverting the done/err flash to idle."""
        name, ts, last = self.snapshot()
        if name in ("done", "err") and vp.now_ts() - ts > FLASH_SECONDS:
            self.set("idle")
            name = "idle"
        return name, last


state = State()

_LABELS = {
    "idle": f"准备就绪 — 按住[{KEY_NAME}]说话", "rec": "🔴 录音中…",
    "proc": "⏳ 转写中…", "done": "✅ 已插入", "err": "⚠️ 失败/太短",
}


def get_display():
    name, last = state.display()
    eng = "SenseVoice" if ENGINE == "sensevoice" else "Whisper"
    return name, f"[{eng}] " + _LABELS.get(name, name), last


def copy_last():
    _, _, last = state.snapshot()
    if last:
        vp.copy_to_clipboard(last)


# --- recording -----------------------------------------------------------------
class Recorder:
    def __init__(self):
        self.q: "queue.Queue[np.ndarray]" = queue.Queue()
        self.stream = None
        self.active = False

    def _cb(self, indata, frames, t, status):
        self.q.put(indata.copy())

    def start(self):
        if self.active:
            return
        self.active = True
        while not self.q.empty():
            self.q.get()
        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                     dtype="float32", callback=self._cb)
        self.stream.start()

    def stop(self) -> np.ndarray:
        if not self.active:
            return np.zeros(0, dtype=np.float32)
        self.active = False
        try:
            self.stream.stop()
            self.stream.close()
        finally:
            self.stream = None
        chunks = []
        while not self.q.empty():
            chunks.append(self.q.get())
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).flatten().astype(np.float32)


rec = Recorder()


# --- transcription engines -----------------------------------------------------
def _pick_whisper_backend() -> str:
    global _whisper_backend
    if _whisper_backend:
        return _whisper_backend
    if vp.IS_MAC:
        try:
            import mlx_whisper  # noqa: F401
            _whisper_backend = "mlx"
            return _whisper_backend
        except Exception:
            pass
    _whisper_backend = "faster"
    return _whisper_backend


def _whisper_mlx(audio: np.ndarray) -> str:
    global _mlx
    if _mlx is None:
        import mlx_whisper as _m
        _mlx = _m
    kwargs = {"path_or_hf_repo": WHISPER_MODEL_ENV or "mlx-community/whisper-large-v3-turbo"}
    if LANG:
        kwargs["language"] = LANG
    if PROMPT:
        kwargs["initial_prompt"] = PROMPT
    return _mlx.transcribe(audio, **kwargs).get("text", "").strip()


def _whisper_faster(audio: np.ndarray) -> str:
    global _fw_model
    if _fw_model is None:
        from faster_whisper import WhisperModel
        _fw_model = WhisperModel(WHISPER_MODEL_ENV or "small",
                                 device="cpu", compute_type="int8")
    segments, _info = _fw_model.transcribe(
        audio, language=LANG, initial_prompt=PROMPT, beam_size=5)
    return "".join(seg.text for seg in segments).strip()


def _transcribe_whisper(audio: np.ndarray) -> str:
    if _pick_whisper_backend() == "mlx":
        return _whisper_mlx(audio)
    return _whisper_faster(audio)


def _transcribe_sensevoice(audio: np.ndarray) -> str:
    global _sv_model
    if _sv_model is None:
        from funasr import AutoModel
        _sv_model = AutoModel(model=SENSEVOICE_MODEL, hub="ms", disable_update=True)
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    res = _sv_model.generate(input=audio, cache={}, language=(LANG or "auto"), use_itn=True)
    if not res:
        return ""
    return rich_transcription_postprocess(res[0]["text"]).strip()


def transcribe(audio: np.ndarray) -> str:
    if ENGINE == "sensevoice":
        text = _transcribe_sensevoice(audio)
    else:
        text = _transcribe_whisper(audio)
    return _to_simplified(text)


# --- paste + turn handling -----------------------------------------------------
def paste_text(text: str):
    vp.copy_to_clipboard(text)
    if not AUTO_PASTE:
        return
    time.sleep(0.15)
    vp.paste()


def handle_release():
    audio = rec.stop()
    secs = audio.size / SAMPLE_RATE
    if secs < MIN_SECONDS:
        state.set("err")
        return
    state.set("proc")
    try:
        text = transcribe(audio)
    except Exception as e:
        state.set("err", f"错误: {e}")
        return
    if not text:
        state.set("err")
        return
    paste_text(text)
    state.set("done", text)
    if NOTIFY:
        vp.notify(text)


def on_press(key):
    if key == HOTKEY and not rec.active:
        rec.start()
        state.set("rec")


def on_release(key):
    if key == HOTKEY and rec.active:
        threading.Thread(target=handle_release, daemon=True).start()


def start_listener():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as ln:
        ln.join()


def warmup():
    try:
        transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32))
    except Exception:
        pass


def _redirect_logs_if_no_console():
    """Under Windows pythonw there is no console, so stdout/stderr are None and
    any output (incl. errors) is lost. Send them to voiced.log next to the script."""
    if sys.stdout is None or sys.stderr is None:
        try:
            logp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voiced.log")
            f = open(logp, "a", buffering=1, encoding="utf-8", errors="replace")
            sys.stdout = sys.stderr = f
        except Exception:
            pass


def main():
    _redirect_logs_if_no_console()
    vp.set_accessory_app()  # mac: menu-bar accessory (no Dock icon); no-op elsewhere
    threading.Thread(target=start_listener, daemon=True).start()
    threading.Thread(target=warmup, daemon=True).start()
    create_tray(get_display, copy_last).run()  # blocks on the main thread


if __name__ == "__main__":
    main()
