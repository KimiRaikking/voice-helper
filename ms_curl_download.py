#!/usr/bin/env python3
"""Robust ModelScope downloader using curl byte-range resume.

ModelScope's Python download balloons / fails to resume on flaky corporate
proxies. This fetches each file with `curl -C -` (true HTTP-range resume, never
balloons) into a local folder, then you point voice.env at that folder
(funasr loads a local dir directly — no further network).

    python ms_curl_download.py            # download the configured engine's model(s)
    python ms_curl_download.py all        # sensevoice + paraformer + punc

Honors voice.env: VOICE_PROXY (curl reads HTTPS_PROXY), VOICE_INSECURE (curl -k).
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voiced  # noqa: E402  (loads voice.env, applies proxy/insecure to env)

MODELS_DIR = Path(__file__).resolve().parent / "models"
INSECURE = (os.environ.get("VOICE_INSECURE") or "") == "1"


def _ok(dest, size):
    return dest.exists() and (not size or dest.stat().st_size == size)


def _run_curl(url, dest, resume):
    cmd = ["curl", "-L", "--retry", "10", "--retry-delay", "5",
           "--retry-all-errors", "-o", str(dest), url]
    if resume:
        cmd[1:1] = ["-C", "-"]
    if INSECURE:
        cmd.insert(1, "-k")
    subprocess.run(cmd, check=False)


def _curl(url, dest, size):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if _ok(dest, size):
        print(f"  ✓ 已完整,跳过 {dest.name}")
        return
    if dest.exists() and size and dest.stat().st_size > size:
        dest.unlink()  # over-sized / corrupt -> redo clean
    print(f"  ↓ {dest.name}  ({(size or 0) / 1e6:.1f} MB)", flush=True)
    # 1) try byte-range resume; 2) if still wrong, clean + full re-download
    _run_curl(url, dest, resume=dest.exists())
    if _ok(dest, size):
        return
    if dest.exists():
        dest.unlink()
    print(f"    续传不成,改整文件重下 {dest.name}", flush=True)
    _run_curl(url, dest, resume=False)
    if not _ok(dest, size):
        raise RuntimeError(
            f"{dest.name} 下载不完整 ({dest.stat().st_size if dest.exists() else 0}/{size})")


def dl_model(model_id):
    from modelscope.hub.api import HubApi
    files = HubApi().get_model_files(model_id, revision="master", recursive=True)
    name = model_id.split("/")[-1]
    out = MODELS_DIR / name
    print(f"== {model_id} -> {out}")
    for f in files:
        if f.get("Type") == "tree":
            continue
        path = f["Path"]
        if path.startswith(("example/", "fig/")) or path == "README.md":
            continue  # skip demos/images/readme
        url = f"https://www.modelscope.cn/models/{model_id}/resolve/master/{path}"
        _curl(url, out / path, f.get("Size", 0))
    print(f"✅ {name} 完成 -> {out}")
    return out


def models_for(engine):
    # Always the canonical repo ids (voiced.*_MODEL may be a local path post-curldl).
    if engine == "sensevoice":
        return [voiced.SENSEVOICE_REPO]
    if engine == "paraformer":
        return [voiced.PARAFORMER_REPO, voiced.PUNC_REPO] if voiced.PUNC_MODEL \
            else [voiced.PARAFORMER_REPO]
    return []


def _set_env(key, val):
    envf = Path(__file__).resolve().parent / "voice.env"
    lines = envf.read_text(encoding="utf-8").splitlines() if envf.exists() else []
    hit = False
    for i, ln in enumerate(lines):
        if ln.strip().startswith(key + "="):
            lines[i] = f"{key}={val}"
            hit = True
    if not hit:
        lines.append(f"{key}={val}")
    envf.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _key_for(model_id):
    return ("SENSEVOICE_MODEL" if "SenseVoice" in model_id else
            "VOICE_PUNC" if "punc" in model_id else "PARAFORMER_MODEL")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        ids = [voiced.SENSEVOICE_REPO, voiced.PARAFORMER_REPO]
        if voiced.PUNC_MODEL:
            ids.append(voiced.PUNC_REPO)
    else:
        ids = models_for(voiced.ENGINE)
    if not ids:
        print(f"引擎 {voiced.ENGINE} 不是 ModelScope 模型,无需此下载器。")
        return
    print("\n下好了,已把 voice.env 指向本地目录(funasr 直接读,不再联网):")
    for m in ids:
        p = dl_model(m)
        _set_env(_key_for(m), str(p))
        print(f"  {_key_for(m)}={p}")
    print("\n接着重启: bash voicectl.sh restart")


if __name__ == "__main__":
    main()
