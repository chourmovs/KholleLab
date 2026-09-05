#!/usr/bin/env python3
"""Diagnose private local inference from a deployment host or Compose backend."""
import json
import os
import time
import urllib.error
import urllib.request

backend = os.getenv("BACKEND_URL", "http://localhost:8000/api").rstrip("/")
inference = os.getenv("LOCAL_LLM_BASE_URL", "http://inference:8080/v1").rstrip("/")

def get(url: str):
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, json.load(response), (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        return exc.code, None, (time.perf_counter() - started) * 1000
    except (urllib.error.URLError, TimeoutError):
        return None, None, (time.perf_counter() - started) * 1000

status_code, status, latency = get(f"{backend}/inference/status")
provider = (status or {}).get("provider", os.getenv("LLM_PROVIDER", "unknown"))
print(f"Provider: {provider}")
print(f"Backend status: {(status or {}).get('status', f'HTTP {status_code or "unreachable"}')}")
health_code, _, health_latency = get(f"{inference.removesuffix('/v1')}/health")
print(f"llama.cpp health: {health_code or 'UNREACHABLE'}")
models_code, models, _ = get(f"{inference}/models")
model = (status or {}).get("model")
if models_code == 200 and models and models.get("data"):
    model = models["data"][0].get("id", model)
print(f"Model: {model or 'unknown'}")
completion = "SKIP (model not ready)"
if (status or {}).get("status") == "ready":
    body = json.dumps({"model": model, "prompt": "Reply OK", "max_tokens": 4}).encode()
    request = urllib.request.Request(f"{inference}/completions", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            completion = "PASS" if response.status == 200 else f"FAIL ({response.status})"
    except (urllib.error.URLError, TimeoutError):
        completion = "FAIL"
print(f"Completion: {completion}")
print(f"Latency: {health_latency if health_code else latency:.1f} ms")
