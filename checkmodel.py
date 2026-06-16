#!/usr/bin/env python3
"""Pinpoint a model-file mismatch: compare what configuration.json expects vs
the actual files on disk (char-exact), so spectok/specctok ambiguity is settled.

    python checkmodel.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voiced  # noqa: E402

d = (voiced.SENSEVOICE_MODEL if voiced.ENGINE == "sensevoice"
     else voiced.PARAFORMER_MODEL if voiced.ENGINE == "paraformer"
     else (voiced.WHISPER_MODEL_ENV or ""))
print("引擎:", voiced.ENGINE)
print("模型目录:", d)
print("目录存在:", os.path.isdir(str(d)))
if not os.path.isdir(str(d)):
    sys.exit("模型目录不存在 -> 没下到本地")

files = sorted(os.listdir(d))
hits = [f for f in files if "spec" in f.lower() or "bpe" in f.lower()]
print("含 spec/bpe 的实际文件:", hits or "(无!)")

cfgp = os.path.join(d, "configuration.json")
if not os.path.exists(cfgp):
    sys.exit("缺少 configuration.json")
cfg = json.load(open(cfgp, encoding="utf-8"))
bpe = (cfg.get("tokenizer_conf") or {}).get("bpemodel")
print("配置期望 bpemodel:", repr(bpe))

if not bpe:
    print("配置里 bpemodel 为空 —— 不该缺这个文件")
else:
    full = os.path.join(d, bpe)
    if os.path.exists(full):
        print(f"==> ✅ 匹配且存在 ({os.path.getsize(full)} 字节)")
    else:
        print("==> ❌ 配置期望的文件不存在!逐字对比:")
        print(f"     配置期望: {bpe!r}")
        for f in hits:
            print(f"     实际文件: {f!r}  相同={f == bpe}")
        print("   结论:实际文件名与配置不一致(下载缺失或拼写不同)")
