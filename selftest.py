#!/usr/bin/env python3
"""Basic self-test — no microphone needed. Verifies the pipeline:
  1) config + resolved model path (local vs repo id)
  2) model loads OFFLINE + inference runs (synthetic audio, must not crash)
  3) real transcription on a bundled example .wav, if present
  4) auto-correction layer (corrections.txt)
  5) clipboard copy/read

    python selftest.py
Exit code 0 = all core checks passed.
"""
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voiced  # noqa: E402

OK, FAIL = "✅", "❌"
errors = []


def step(name, fn):
    try:
        fn()
        print(f"{OK} {name}")
    except Exception as e:
        print(f"{FAIL} {name}: {e}")
        errors.append(name)


def _find_example_wav():
    for m in (voiced.SENSEVOICE_MODEL, voiced.PARAFORMER_MODEL):
        if m and os.path.isdir(m):
            for root, _d, files in os.walk(m):
                for f in files:
                    if f.lower().endswith(".wav"):
                        return os.path.join(root, f)
    return None


def _load_wav(path):
    with wave.open(path, "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if w.getnchannels() == 2:
        audio = audio.reshape(-1, 2).mean(axis=1)
    return audio, sr


def main():
    print("== 配置 ==")
    print(f"  引擎: {voiced.ENGINE}")
    model = (voiced.SENSEVOICE_MODEL if voiced.ENGINE == "sensevoice"
             else voiced.PARAFORMER_MODEL if voiced.ENGINE == "paraformer"
             else (voiced.WHISPER_MODEL_ENV or "whisper"))
    is_local = os.path.isdir(str(model))
    print(f"  模型: {model}")
    print(f"  本地离线加载: {'是 ' + OK if is_local else '否 ⚠ (会联网下载)'}")

    print("\n== 测试 ==")
    # 2) load + inference on synthetic audio (quiet noise, not pure silence —
    #    silence makes SeACo-Paraformer emit 0 tokens -> [-1,512] error)
    step("模型加载 + 推理(合成音频,不崩即过)",
         lambda: voiced.transcribe(
             (np.random.randn(voiced.SAMPLE_RATE * 2) * 0.01).astype(np.float32)))

    # 3) real transcription on a bundled example wav, if any
    wav = _find_example_wav()
    if wav:
        def real():
            audio, sr = _load_wav(wav)
            if sr != voiced.SAMPLE_RATE:
                raise RuntimeError(f"示例音频 {sr}Hz,非16k,跳过真实转写")
            txt = voiced.transcribe(audio.astype(np.float32))
            print(f"     示例音频转写结果: {txt!r}")
            if not txt:
                raise RuntimeError("转写结果为空")
        step(f"真实转写示例音频 ({os.path.basename(wav)})", real)
    else:
        print("·  (模型目录无示例 .wav,跳过真实转写)")

    # 4) correction layer
    def corr():
        out = voiced.apply_corrections("测试食盐")
        print(f"     '测试食盐' -> {out!r}")
    step("字词纠正层", corr)

    # 5) clipboard
    def clip():
        import pyperclip
        voiced.vp.copy_to_clipboard("voice-helper-selftest-✓")
        got = pyperclip.paste()
        if "selftest" not in got:
            raise RuntimeError(f"剪贴板读回不符: {got!r}")
    step("剪贴板复制/读取", clip)

    print("\n== 结果 ==")
    if errors:
        print(f"{FAIL} 失败项: {', '.join(errors)}")
        sys.exit(1)
    print(f"{OK} 全部通过 — 链路正常(就差真实麦克风音频)。")


if __name__ == "__main__":
    main()
