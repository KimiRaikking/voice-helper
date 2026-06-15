#!/usr/bin/env python3
"""Pre-download the model for the currently configured engine, with progress.

Reads voice.env (so VOICE_ENGINE + VOICE_PROXY/CA apply), then downloads:
  - sensevoice -> SENSEVOICE_MODEL from ModelScope
  - paraformer -> PARAFORMER_MODEL from ModelScope
  - whisper    -> WHISPER_MODEL (mac: mlx repo; win: faster-whisper)

    python download_model.py            # download the configured engine's model
    python download_model.py all        # download sensevoice + paraformer

Auto-retries on dropped connections (corporate proxies often kill long
transfers); ModelScope/HF downloads resume from partial files, so each retry
makes progress. Ctrl+C to stop.
"""
import os
import sys
import time

import numpy as np

# Importing voiced loads voice.env and applies VOICE_PROXY / VOICE_CA / mirror.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voiced  # noqa: E402

TRIES = int(os.environ.get("VOICE_DL_TRIES", "60"))
WAIT = int(os.environ.get("VOICE_DL_WAIT", "5"))


def _retry(name, fn):
    for i in range(1, TRIES + 1):
        try:
            print(f"[{i}/{TRIES}] 下载 {name} ...(已下部分会续传)", flush=True)
            fn()
            print(f"✅ {name} 完成")
            return True
        except KeyboardInterrupt:
            print("已手动中断。")
            return False
        except Exception as e:
            print(f"  ⚠ 中断/失败: {e}", flush=True)
            time.sleep(WAIT)
    print(f"❌ {name} 多次重试仍失败,放弃。")
    return False


def _ms(model):
    from funasr import AutoModel
    AutoModel(model=model, hub="ms", disable_update=True)


def dl_sensevoice():
    return _retry("SenseVoice", lambda: _ms(voiced.SENSEVOICE_MODEL))


def dl_paraformer():
    return _retry("Paraformer", lambda: _ms(voiced.PARAFORMER_MODEL))


def dl_whisper():
    return _retry("Whisper", lambda: voiced.transcribe(
        np.zeros(voiced.SAMPLE_RATE, dtype="float32")))


def dl_current():
    print(f"engine={voiced.ENGINE}  proxy={os.environ.get('HTTPS_PROXY') or '(none)'}")
    if voiced.ENGINE == "sensevoice":
        dl_sensevoice()
    elif voiced.ENGINE == "paraformer":
        dl_paraformer()
    else:
        dl_whisper()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        dl_sensevoice()
        dl_paraformer()
    else:
        dl_current()


if __name__ == "__main__":
    main()
