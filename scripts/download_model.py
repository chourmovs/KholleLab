#!/usr/bin/env python3
"""Idempotently resolve and download one GGUF artifact from Hugging Face."""
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

repo = os.getenv("LOCAL_LLM_HF_REPO", "Qwen/Qwen3-4B-GGUF")
quant = os.getenv("LOCAL_LLM_QUANT", "Q4_K_M")
target = Path(os.getenv("LOCAL_LLM_DESTINATION", "/models/model.gguf"))
token = os.getenv("HF_TOKEN")
headers = {"Authorization": f"Bearer {token}"} if token else {}

def log(message): print(f"[model] {message}", flush=True)
def request(url): return urllib.request.Request(url, headers=headers)

log(f"target {repo} {quant}")
log(f"checking {target}")
if target.is_file() and target.stat().st_size > 0:
    log("existing model found")
    log("download skipped")
    sys.exit(0)

target.parent.mkdir(parents=True, exist_ok=True)
part = target.with_suffix(target.suffix + ".part")
part.unlink(missing_ok=True)
try:
    with urllib.request.urlopen(request(f"https://huggingface.co/api/models/{repo}"), timeout=30) as response:
        metadata = json.load(response)
    candidates = [item["rfilename"] for item in metadata.get("siblings", []) if item["rfilename"].lower().endswith(".gguf") and quant.lower() in item["rfilename"].lower()]
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one {quant} GGUF artifact, found {len(candidates)}")
    filename = candidates[0]
    size = next((item.get("size") for item in metadata.get("siblings", []) if item["rfilename"] == filename), None)
    if size and shutil.disk_usage(target.parent).free < size * 2:
        raise RuntimeError("insufficient free space for model and partial download")
    url = f"https://huggingface.co/{repo}/resolve/main/{filename}"
    log(f"resolved {filename}")
    for attempt in range(1, 4):
        try:
            log(f"downloading... (attempt {attempt}/3)")
            with urllib.request.urlopen(request(url), timeout=90) as source, part.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            if part.stat().st_size <= 0:
                raise RuntimeError("downloaded file is empty")
            part.replace(target)
            log("download complete")
            log(f"size: {target.stat().st_size} bytes")
            log("ready")
            break
        except Exception:
            part.unlink(missing_ok=True)
            if attempt == 3: raise
            time.sleep(attempt * 2)
except Exception as exc:
    log(f"ERROR: {exc}")
    sys.exit(1)
