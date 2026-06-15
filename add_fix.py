#!/usr/bin/env python3
"""Add an auto-correction rule — applied to EVERY transcription, all engines.
Takes effect on the next utterance (corrections.txt is re-read each time).

    python add_fix.py 食盐 时延     # 把"食盐"自动改成"时延"
    python add_fix.py              # 列出当前所有纠正规则

适合给 AI agent 用:发现某个词总被转错,一条命令登记,以后自动纠正。
"""
import sys
from pathlib import Path

FILE = Path(__file__).resolve().parent / "corrections.txt"


def rules():
    if not FILE.exists():
        return []
    out = []
    for line in FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=>" in line:
            out.append(line)
    return out


def main():
    args = [a.strip() for a in sys.argv[1:] if a.strip()]
    if not args:
        cur = rules()
        print("当前纠正规则:")
        print("\n".join("  " + r for r in cur) if cur else "  (空)")
        print(f"文件: {FILE}")
        return
    if len(args) != 2:
        print("用法: python add_fix.py 错词 对词")
        return
    wrong, right = args
    rule = f"{wrong}=>{right}"
    existing = rules()
    if rule in existing:
        print(f"(已存在) {rule}")
        return
    if not FILE.exists():
        FILE.write_text("# 自动纠正:每行 错词=>对词;转写后实时套用,所有引擎生效。\n",
                        encoding="utf-8")
    with FILE.open("a", encoding="utf-8") as f:
        f.write(rule + "\n")
    print(f"✅ 已添加: {rule}")


if __name__ == "__main__":
    main()
