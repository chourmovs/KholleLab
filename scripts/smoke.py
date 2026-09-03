#!/usr/bin/env python3
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

api = os.getenv("SMOKE_API_URL", "http://localhost:8000/api")
frontend = os.getenv("SMOKE_FRONTEND_URL", "http://localhost:3000")


def get_json(url: str):
    with urlopen(url, timeout=10) as response:
        return json.load(response)


def send_json(url: str, method: str, payload: dict, expected: int = 200):
    request = Request(url, method=method, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        assert error.code == expected
        return json.load(error)
    assert response.status == expected
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
attempt = send_json(f"{api}/attempts", "POST", {"problem_id": catalogue[0]["id"]}, 201)
assert attempt["status"] == "draft" and attempt["revision"] == 0
solution = """On pose $x > 0$.

Comme
$$
(\\sqrt{x}-1/\\sqrt{x})^2 \\geq 0,
$$
on obtient le résultat."""
saved = send_json(f"{api}/attempts/{attempt['id']}", "PATCH", {"solution_markdown": solution, "elapsed_seconds": 12, "expected_revision": 0})
assert saved["revision"] == 1 and get_json(f"{api}/attempts/{attempt['id']}")["solution_markdown"] == solution
assert send_json(f"{api}/attempts/{attempt['id']}", "PATCH", {"solution_markdown": "stale", "elapsed_seconds": 12, "expected_revision": 0}, 409)["error"] == "attempt_conflict"
submitted = send_json(f"{api}/attempts/{attempt['id']}/submit", "POST", {"expected_revision": 1})
assert submitted["status"] == "submitted" and "reference_solution" not in json.dumps(submitted)
assert send_json(f"{api}/attempts/{attempt['id']}", "PATCH", {"solution_markdown": "locked", "elapsed_seconds": 12, "expected_revision": 2}, 409)["error"] == "attempt_submitted"
print("[PASS] Attempt lifecycle, concurrency, and correction isolation")
with urlopen(frontend, timeout=10) as response:
    assert "KHOLLELAB" in response.read().decode()
print("[PASS] Frontend reachable")
print("Smoke test passed.")
