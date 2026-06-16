#!/usr/bin/env python3
"""Pre-download model files for the configured engine (download only — does NOT
load the model, so no worker subprocesses are spawned).

    python download_model.py            # download the configured engine's model
    python download_model.py all        # sensevoice + paraformer (+punc)

Reads voice.env (VOICE_PROXY / VOICE_CA / VOICE_INSECURE / mirror apply).
A lock file prevents two downloads running at once. Auto-retries on dropped
connections; already-downloaded files are skipped, so each retry makes progress.
Ctrl+C to stop.
"""
import os
import sys
import time
from pathlib import Path

# Importing voiced loads voice.env and applies proxy/CA/mirror (no daemon starts).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voiced  # noqa: E402

TRIES = int(os.environ.get("VOICE_DL_TRIES", "60"))
WAIT = int(os.environ.get("VOICE_DL_WAIT", "5"))
LOCK = Path(__file__).resolve().parent / ".download.lock"


def _retry(name, fn):
    for i in range(1, TRIES + 1):
        try:
            print(f"[{i}/{TRIES}] 下载 {name} ...(已下文件会跳过)", flush=True)
            fn()
            print(f"✅ {name} 完成")
            return True
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"  ⚠ 中断/失败: {e}", flush=True)
            time.sleep(WAIT)
    print(f"❌ {name} 多次重试仍失败,放弃。")
    return False


def _ms(repo):
    """Download a ModelScope repo's files only (no model loading)."""
    try:
        from modelscope import snapshot_download
    except Exception:
        from modelscope.hub.snapshot_download import snapshot_download
    snapshot_download(repo)


def _hf(repo):
    from huggingface_hub import snapshot_download
    snapshot_download(repo)


def dl_sensevoice():
    return _retry("SenseVoice", lambda: _ms(voiced.SENSEVOICE_MODEL))


def dl_paraformer():
    ok = _retry("Paraformer", lambda: _ms(voiced.PARAFORMER_MODEL))
    if voiced.PUNC_MODEL:
        ok = _retry("标点模型", lambda: _ms(voiced.PUNC_MODEL)) and ok
    return ok


def dl_whisper():
    repo = voiced.WHISPER_MODEL_ENV or (
        "mlx-community/whisper-large-v3-turbo" if voiced.vp.IS_MAC else "Systran/faster-whisper-small")
    return _retry(f"Whisper ({repo})", lambda: _hf(repo))


def dl_current():
    print(f"engine={voiced.ENGINE}  proxy={os.environ.get('HTTPS_PROXY') or '(none)'}")
    {"sensevoice": dl_sensevoice, "paraformer": dl_paraformer}.get(
        voiced.ENGINE, dl_whisper)()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        dl_sensevoice()
        dl_paraformer()
    else:
        dl_current()


if __name__ == "__main__":
    if LOCK.exists():
        print(f"⚠ 已有下载在运行(锁文件存在)。确认没有别的下载进程后,删除再试:\n  {LOCK}")
        sys.exit(1)
    LOCK.write_text(str(os.getpid()))
    try:
        main()
    except KeyboardInterrupt:
        print("\n已手动中断。")
    finally:
        try:
            LOCK.unlink()
        except OSError:
            pass
