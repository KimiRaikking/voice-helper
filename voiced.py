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

# Make sibling modules (vplatform, tray) importable regardless of how we're
# launched — the embeddable Python (portable build) does NOT add the script dir.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


def _apply_proxy():
    """If VOICE_PROXY is set (e.g. copied from `git config --get http.proxy`),
    route model downloads (HuggingFace / ModelScope) through it."""
    p = (os.environ.get("VOICE_PROXY") or "").strip()
    if p:
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            os.environ.setdefault(k, p)
    # HuggingFace mirror / internal endpoint for Whisper models (ModelScope unaffected).
    hf = (os.environ.get("VOICE_HF_ENDPOINT") or "").strip()
    if hf:
        os.environ.setdefault("HF_ENDPOINT", hf)


def _apply_tls():
    """Corporate proxies often do TLS interception with a self-signed root CA,
    which breaks Python downloads ('self signed certificate in certificate chain').
    VOICE_CA = path to the corporate CA bundle (reuse git's: `git config --get
    http.sslCAInfo`). VOICE_INSECURE=1 = skip verification (last resort)."""
    ca = (os.environ.get("VOICE_CA") or "").strip()
    if ca and os.path.exists(ca):
        for k in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
            os.environ.setdefault(k, ca)
    elif (os.environ.get("VOICE_INSECURE") or "") == "1":
        try:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            import requests
            import urllib3
            urllib3.disable_warnings()
            _orig = requests.Session.request

            def _no_verify(self, *a, **k):
                k.setdefault("verify", False)
                return _orig(self, *a, **k)

            requests.Session.request = _no_verify
        except Exception:
            pass


_apply_proxy()
_apply_tls()

SAMPLE_RATE = 16000
ENGINE = os.environ.get("VOICE_ENGINE", "whisper").lower()  # whisper | sensevoice | paraformer
WHISPER_MODEL_ENV = os.environ.get("WHISPER_MODEL") or None
# Canonical ModelScope repo ids — used by the downloaders (never change to a
# local path). The *_MODEL values below are what's LOADED, and may be overridden
# to a local directory (e.g. by ms_curl_download.py) — so loaders and downloaders
# must not share the same variable.
SENSEVOICE_REPO = "iic/SenseVoiceSmall"
PARAFORMER_REPO = "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
PUNC_REPO = "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
_HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve_model(value):
    """If value is a repo id but a local copy already exists (curl -> models/<name>,
    or snapshot -> modelscope cache), return that local dir so funasr loads it
    WITHOUT hitting the ModelScope API (which fails behind an auth proxy: 407)."""
    value = (value or "").strip()
    if not value or os.path.isdir(value):
        return value
    name = value.split("/")[-1]
    candidates = [
        os.path.join(_HERE, "models", name),                                   # curldl
        os.path.expanduser(os.path.join("~/.cache/modelscope/hub/models", value)),  # snapshot
    ]
    for c in candidates:
        try:
            if os.path.isdir(c) and any(f.endswith(".pt") for f in os.listdir(c)):
                return c
        except OSError:
            pass
    return value


SENSEVOICE_MODEL = _resolve_model(os.environ.get("SENSEVOICE_MODEL", SENSEVOICE_REPO))
PARAFORMER_MODEL = _resolve_model(os.environ.get("PARAFORMER_MODEL", PARAFORMER_REPO))
# Punctuation model for Paraformer (it has none by default). Empty = no punctuation.
PUNC_MODEL = _resolve_model(os.environ.get("VOICE_PUNC", PUNC_REPO))
HOTWORD_ENV = (os.environ.get("VOICE_HOTWORD") or "").strip()
HOTWORDS_FILE = os.path.join(_HERE, "hotwords.txt")
CORRECTIONS_FILE = os.path.join(_HERE, "corrections.txt")
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


def _resolve_hotkeys(name):
    keys = {KEY_MAP.get(name, Key.alt_r)}
    # On many Windows layouts the Right Alt key is AltGr -> pynput reports alt_gr.
    if name in ("alt_r", "alt") and hasattr(Key, "alt_gr"):
        keys.add(Key.alt_gr)
    return keys


HOTKEYS = _resolve_hotkeys(KEY_NAME)

_mlx = None
_fw_model = None
_whisper_backend = None  # "mlx" | "faster"
_sv_model = None         # lazily-loaded SenseVoice (funasr) model
_pf_model = None         # lazily-loaded SeACo-Paraformer (funasr) model

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


_ENGINE_LABEL = {"sensevoice": "SenseVoice", "paraformer": "Paraformer"}


def get_display():
    name, last = state.display()
    eng = _ENGINE_LABEL.get(ENGINE, "Whisper")
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


def _fa_init(model, **extra):
    """Build funasr AutoModel kwargs. For a LOCAL directory, omit hub='ms' so it
    never hits the ModelScope API (which fails on offline / TLS-intercepted nets);
    only a repo id needs the hub."""
    init = {"model": model, "disable_update": True, **extra}
    if not os.path.isdir(str(model)):
        init["hub"] = "ms"
    return init


def _transcribe_sensevoice(audio: np.ndarray) -> str:
    global _sv_model
    if _sv_model is None:
        from funasr import AutoModel
        _sv_model = AutoModel(**_fa_init(SENSEVOICE_MODEL))
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    res = _sv_model.generate(input=audio, cache={}, language=(LANG or "auto"), use_itn=True)
    if not res:
        return ""
    return rich_transcription_postprocess(res[0]["text"]).strip()


def read_hotwords() -> str:
    """Merge VOICE_HOTWORD env + hotwords.txt (read fresh each call, so adding a
    word takes effect on the very next utterance — no restart needed)."""
    words = HOTWORD_ENV.split() if HOTWORD_ENV else []
    try:
        with open(HOTWORDS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    words += line.split()
    except FileNotFoundError:
        pass
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return " ".join(out)


_pf_hotword_ok = True  # SeACo hotword path crashes on some funasr versions ([-1,512])


def _transcribe_paraformer(audio: np.ndarray) -> str:
    global _pf_model, _pf_hotword_ok
    if _pf_model is None:
        from funasr import AutoModel
        extra = {"punc_model": PUNC_MODEL} if PUNC_MODEL else {}
        _pf_model = AutoModel(**_fa_init(PARAFORMER_MODEL, **extra))
    hot = read_hotwords()

    def _gen(use_hot):
        kw = {"input": audio, "cache": {}}
        if use_hot and hot:
            kw["hotword"] = hot  # SeACo-Paraformer: space-separated bias words
        return _pf_model.generate(**kw)

    res = None
    if _pf_hotword_ok and hot:
        try:
            res = _gen(True)
        except Exception as e:
            # e.g. "tensor with negative dimension -1: [-1,512]" — SeACo bias
            # broken on this funasr/torch build; fall back to plain Paraformer.
            print(f"⚠ Paraformer 热词不可用,改用无热词(纠正表仍生效): {e}", flush=True)
            _pf_hotword_ok = False
    if res is None:
        res = _gen(False)
    if not res:
        return ""
    # Paraformer-zh returns characters possibly space-separated; collapse for Chinese.
    return res[0].get("text", "").replace(" ", "").strip()


def read_corrections():
    """Parse corrections.txt into [(wrong, right)], re-read each call so edits
    take effect immediately. Line format: 错词=>对词  (# comments ignored)."""
    pairs = []
    try:
        with open(CORRECTIONS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=>" not in line:
                    continue
                wrong, right = line.split("=>", 1)
                wrong, right = wrong.strip(), right.strip()
                if wrong:
                    pairs.append((wrong, right))
    except FileNotFoundError:
        pass
    # apply longer keys first so specific phrases win over their substrings
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs


def apply_corrections(text: str) -> str:
    if not text:
        return text
    for wrong, right in read_corrections():
        if wrong in text:
            text = text.replace(wrong, right)
    return text


def transcribe(audio: np.ndarray) -> str:
    if ENGINE == "sensevoice":
        text = _transcribe_sensevoice(audio)
    elif ENGINE == "paraformer":
        text = _transcribe_paraformer(audio)
    else:
        text = _transcribe_whisper(audio)
    return apply_corrections(_to_simplified(text))


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
    if key in HOTKEYS and not rec.active:
        rec.start()
        state.set("rec")


def on_release(key):
    if key in HOTKEYS and rec.active:
        threading.Thread(target=handle_release, daemon=True).start()


def start_listener():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as ln:
        ln.join()


def warmup():
    try:
        # quiet noise, not pure silence: silence makes SeACo-Paraformer emit 0
        # tokens -> a [-1,512] tensor error on some funasr versions.
        transcribe((np.random.randn(SAMPLE_RATE) * 0.01).astype(np.float32))
    except Exception:
        pass


def _persist_engine(name):
    """Write VOICE_ENGINE=name into voice.env so the choice survives restarts."""
    path = os.path.join(_HERE, "voice.env")
    try:
        lines = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []
        lines = [ln for ln in lines if not ln.strip().startswith("VOICE_ENGINE=")]
        lines.append(f"VOICE_ENGINE={name}")
        open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    except Exception:
        pass


def switch_engine(name):
    """Switch engine in place — no restart. Drops the loaded model so the new
    engine loads lazily on the next utterance; persists the choice to voice.env."""
    global ENGINE, _mlx, _fw_model, _whisper_backend, _sv_model, _pf_model
    name = (name or "").lower()
    if name not in ("whisper", "sensevoice", "paraformer") or name == ENGINE:
        return
    ENGINE = name
    _mlx = _fw_model = _whisper_backend = _sv_model = _pf_model = None
    _persist_engine(name)
    print(f"切换引擎 -> {name}", flush=True)
    threading.Thread(target=warmup, daemon=True).start()  # preload new model


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
    model = SENSEVOICE_MODEL if ENGINE == "sensevoice" else \
        PARAFORMER_MODEL if ENGINE == "paraformer" else (WHISPER_MODEL_ENV or "whisper")
    print(f"\n===== voiced 启动 {time.strftime('%Y-%m-%d %H:%M:%S')} | "
          f"engine={ENGINE} | model={model} =====", flush=True)
    vp.set_accessory_app()  # mac: menu-bar accessory (no Dock icon); no-op elsewhere
    threading.Thread(target=start_listener, daemon=True).start()
    threading.Thread(target=warmup, daemon=True).start()
    create_tray(get_display, copy_last, switch_engine, lambda: ENGINE).run()  # blocks (main thread)


if __name__ == "__main__":
    main()
