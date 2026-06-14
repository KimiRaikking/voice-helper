#!/usr/bin/env python3
"""Voice dictation for the terminal, powered by mlx-whisper (Apple Silicon).

Usage:
    python dictate.py                 # record until Enter, transcribe, copy to clipboard
    python dictate.py --lang zh       # force Chinese
    python dictate.py --lang en       # force English
    python dictate.py --no-copy       # just print, don't touch clipboard
    python dictate.py --paste         # after copying, auto-paste into the previously focused app

Env:
    WHISPER_MODEL   HF repo of the MLX model (default: mlx-community/whisper-large-v3-turbo)
"""
import argparse
import os
import queue
import subprocess
import sys
import threading
import time

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000  # whisper wants 16 kHz mono
MODEL = os.environ.get("WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")


def record_until_enter() -> np.ndarray:
    """Record mono audio at 16 kHz until the user presses Enter."""
    q: "queue.Queue[np.ndarray]" = queue.Queue()
    stop = threading.Event()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"  (audio status: {status})", file=sys.stderr)
        q.put(indata.copy())

    print("🎙️  Recording... speak now, then press Enter to stop.", flush=True)

    # Wait for Enter on a background thread so the stream keeps filling the queue.
    threading.Thread(target=lambda: (sys.stdin.readline(), stop.set()), daemon=True).start()

    chunks = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
        while not stop.is_set():
            try:
                chunks.append(q.get(timeout=0.1))
            except queue.Empty:
                pass
    # Drain anything left in the queue.
    while not q.empty():
        chunks.append(q.get())

    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks, axis=0).flatten().astype(np.float32)


def transcribe(audio: np.ndarray, lang: str | None) -> str:
    import mlx_whisper  # imported late: first call downloads the model

    if audio.size == 0:
        return ""
    kwargs = {"path_or_hf_repo": MODEL}
    if lang:
        kwargs["language"] = lang
    result = mlx_whisper.transcribe(audio, **kwargs)
    return result.get("text", "").strip()


def copy_to_clipboard(text: str) -> None:
    subprocess.run("pbcopy", input=text.encode("utf-8"), check=True)


def auto_paste() -> None:
    # Re-activate whatever app was frontmost before this terminal, then Cmd-V.
    script = (
        'tell application "System Events" to keystroke "v" using command down'
    )
    subprocess.run(["osascript", "-e", script], check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description="Voice dictation -> clipboard via mlx-whisper")
    ap.add_argument("--lang", default=None, help="force language code, e.g. zh / en (default: auto)")
    ap.add_argument("--no-copy", action="store_true", help="don't copy to clipboard")
    ap.add_argument("--paste", action="store_true", help="auto-paste into frontmost app after copy")
    args = ap.parse_args()

    audio = record_until_enter()
    secs = audio.size / SAMPLE_RATE
    if secs < 0.2:
        print("⚠️  No audio captured.", file=sys.stderr)
        return 1

    print(f"⏳ Transcribing {secs:.1f}s with {MODEL} ...", flush=True)
    t0 = time.time()
    text = transcribe(audio, args.lang)
    dt = time.time() - t0

    if not text:
        print("⚠️  Empty transcription.", file=sys.stderr)
        return 1

    print(f"\n📝 ({dt:.1f}s)\n{text}\n")

    if not args.no_copy:
        copy_to_clipboard(text)
        print("📋 Copied to clipboard." + (" Pasting..." if args.paste else " Press Cmd-V to paste."))
        if args.paste:
            time.sleep(0.3)
            auto_paste()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
