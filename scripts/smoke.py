#!/usr/bin/env python3
import json
import os
from urllib.request import urlopen

api = os.getenv("SMOKE_API_URL", "http://localhost:8000/api")
frontend = os.getenv("SMOKE_FRONTEND_URL", "http://localhost:3000")


def get_json(url: str):
    with urlopen(url, timeout=10) as response:
        return json.load(response)


health = get_json(f"{api}/health")
assert health["status"] == "ok"
print("[PASS] API and database health")
assert health["problem_corpus"] == "ok" and health["problem_count"] > 0
print("[PASS] Problem corpus health")
catalogue = get_json(f"{api}/problems")
assert isinstance(catalogue, list) and catalogue
assert all("reference_solution" not in item for item in catalogue)
print("[PASS] Problem catalogue")
detail = get_json(f"{api}/problems/{catalogue[0]['id']}")
assert {"id", "title", "statement"} <= detail.keys()
assert "reference_solution" not in detail
print("[PASS] Problem detail and private reference solution")
with urlopen(frontend, timeout=10) as response:
    assert "KHOLLELAB" in response.read().decode()
print("[PASS] Frontend reachable")
print("Smoke test passed.")
