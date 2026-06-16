#!/usr/bin/env python3
"""Move models to an ASCII-only path and point voice.env there.

Why: on Windows, funasr's SentencePiece tokenizer can't open files under a
non-ASCII path (e.g. D:\\智能运维\\...), so the model 'Not Found' even though
the file exists. The repo/venv can stay where they are (Python handles non-ASCII
paths fine) — only the model DATA needs an ASCII path.

    python fix_model_path.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voiced  # noqa: E402

ENVF = os.path.join(voiced._HERE, "voice.env")


def set_env(key, val):
    lines = []
    if os.path.exists(ENVF):
        lines = open(ENVF, encoding="utf-8").read().splitlines()
    lines = [ln for ln in lines if not ln.strip().startswith(key + "=")]
    lines.append(f"{key}={val}")
    open(ENVF, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def is_ascii(s):
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def main():
    src = os.path.join(voiced._HERE, "models")
    drive = os.path.splitdrive(voiced._HERE)[0]
    target = (drive + os.sep + "voicehelper-models") if drive \
        else os.path.expanduser("~/voicehelper-models")

    if not is_ascii(voiced._HERE):
        print(f"⚠ 当前项目路径含非ASCII字符: {voiced._HERE}")
    print(f"模型将放到纯英文路径: {target}")
    os.makedirs(target, exist_ok=True)

    if os.path.isdir(src):
        for name in os.listdir(src):
            s, d = os.path.join(src, name), os.path.join(target, name)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.move(s, d)
                print(f"  移动 {name} -> {d}")

    # point voice.env at the ASCII model dirs (only those that now exist)
    for repo, key in ((voiced.SENSEVOICE_REPO, "SENSEVOICE_MODEL"),
                      (voiced.PARAFORMER_REPO, "PARAFORMER_MODEL"),
                      (voiced.PUNC_REPO, "VOICE_PUNC")):
        p = os.path.join(target, repo.split("/")[-1])
        if os.path.isdir(p):
            set_env(key, p)
            print(f"  voice.env: {key}={p}")

    print("\n✅ 完成。现在重启: bash voicectl.sh restart  然后 selftest")


if __name__ == "__main__":
    main()
