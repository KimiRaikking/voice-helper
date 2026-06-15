#!/usr/bin/env python3
"""Add hotwords for the Paraformer engine — takes effect on the NEXT utterance
(no restart needed; voiced reads hotwords.txt fresh every transcription).

    python add_hotword.py 时延 推理 吞吐量
    python add_hotword.py            # no args: print current hotwords

Use it the moment a word is mis-transcribed: feed the correct word, say it again,
and the engine biases toward it.
"""
import sys
from pathlib import Path

HOTWORDS = Path(__file__).resolve().parent / "hotwords.txt"


def current():
    if not HOTWORDS.exists():
        return []
    out = []
    for line in HOTWORDS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def main():
    words = [w.strip() for w in sys.argv[1:] if w.strip()]
    existing = current()
    if not words:
        print("当前热词:", " ".join(existing) if existing else "(空)")
        print(f"文件: {HOTWORDS}")
        return
    added = [w for w in words if w not in existing]
    if added:
        if not HOTWORDS.exists():
            HOTWORDS.write_text("# 热词库:每行一个词/短语;Paraformer 引擎每次转写实时读取。\n",
                                encoding="utf-8")
        with HOTWORDS.open("a", encoding="utf-8") as f:
            for w in added:
                f.write(w + "\n")
        print(f"✅ 已添加: {' '.join(added)}")
    else:
        print("(都已存在,未重复添加)")
    print("现有热词:", " ".join(current()))


if __name__ == "__main__":
    main()
