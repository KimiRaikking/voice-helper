#!/usr/bin/env python3
"""Pre-download the model for the currently configured engine, with progress.

Reads voice.env (so VOICE_ENGINE + VOICE_PROXY apply), then downloads:
  - sensevoice -> SENSEVOICE_MODEL from ModelScope
  - paraformer -> PARAFORMER_MODEL from ModelScope
  - whisper    -> WHISPER_MODEL (mac: mlx repo; win: faster-whisper)

    python download_model.py            # download the configured engine's model
    python download_model.py all        # download sensevoice + paraformer

Run it when first setting up behind a corporate proxy:
    git config --global --get http.proxy   # then put that into voice.env VOICE_PROXY
"""
import os
import sys

import numpy as np

# Importing voiced loads voice.env and applies VOICE_PROXY to the environment.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voiced  # noqa: E402


def dl_sensevoice():
    print("↓ SenseVoice ...", flush=True)
    from funasr import AutoModel
    AutoModel(model=voiced.SENSEVOICE_MODEL, hub="ms", disable_update=True)
    print("✅ SenseVoice OK")


def dl_paraformer():
    print("↓ Paraformer ...", flush=True)
    from funasr import AutoModel
    AutoModel(model=voiced.PARAFORMER_MODEL, hub="ms", disable_update=True)
    print("✅ Paraformer OK")


def dl_current():
    print(f"engine={voiced.ENGINE}  proxy={os.environ.get('HTTPS_PROXY') or '(none)'}")
    voiced.transcribe(np.zeros(voiced.SAMPLE_RATE, dtype="float32"))
    print("✅ done")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        dl_sensevoice()
        dl_paraformer()
    else:
        dl_current()


if __name__ == "__main__":
    main()
