#!/usr/bin/env python3
import json
import os
from urllib.error import HTTPError
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, Request, build_opener

opener = build_opener(HTTPCookieProcessor(CookieJar()))
urlopen = opener.open

frontend = os.getenv("SMOKE_FRONTEND_URL", "http://frontend:3000")
api = os.getenv("SMOKE_API_URL", f"{frontend}/api")


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
curriculum = get_json(f"{api}/curriculum")
assert len(curriculum["levels"]) == 5 and len(curriculum["difficulties"]) == 5
print("[PASS] Curriculum metadata")
for level, label in (("seconde", "Seconde"), ("premiere", "Première"), ("terminale", "Terminale"), ("maths-sup", "Maths Sup"), ("maths-spe", "Maths Spé")):
    selection = get_json(f"{api}/problems/select?level={level}&difficulty=2")
    assert selection["problem"]["curriculum"]["level"] == level
    assert "reference_solution" not in json.dumps(selection)
    print(f"[PASS] {label} selection")
fallback = get_json(f"{api}/problems/select?level=seconde&difficulty=5")
assert fallback["fallback_used"] and fallback["actual_difficulty"] == 3
print("[PASS] Difficulty fallback")
print("[PASS] Reference solution isolation")
catalogue = get_json(f"{api}/problems")
assert isinstance(catalogue, list) and catalogue
assert all("reference_solution" not in item for item in catalogue)
print("[PASS] Problem catalogue")
detail = get_json(f"{api}/problems/{catalogue[0]['id']}")
assert {"id", "title", "statement"} <= detail.keys()
assert "reference_solution" not in detail
print("[PASS] Problem detail and private reference solution")

def assert_no_private_problem_fields(value):
    if isinstance(value, dict):
        assert "reference_solution" not in value
        for child in value.values(): assert_no_private_problem_fields(child)
    elif isinstance(value, list):
        for child in value: assert_no_private_problem_fields(child)

learning = send_json(f"{api}/sessions", "POST", {"problem_id": catalogue[0]["id"]}, 201)
assert_no_private_problem_fields(learning)
session_id, session_attempt_id = learning["session_id"], learning["current_attempt_id"]
assert session_attempt_id and any(item["id"] == session_attempt_id for item in learning["attempts"])
session_saved = send_json(f"{api}/attempts/{session_attempt_id}", "PATCH", {"solution_markdown": "Travail de séance", "elapsed_seconds": 7, "expected_revision": 0})
active = get_json(f"{api}/sessions/active/latest")
assert active["session_id"] == session_id and active["final_work"] == "Travail de séance"
assert_no_private_problem_fields(active)
send_json(f"{api}/attempts/{session_attempt_id}/submit", "POST", {"expected_revision": session_saved["revision"]})
history = get_json(f"{api}/sessions")
assert history[0]["session_id"] == session_id and history[0]["status"] == "completed"
assert_no_private_problem_fields(history)
adaptive = get_json(f"{api}/problems/select?level={catalogue[0]['curriculum']['level']}&difficulty={catalogue[0]['curriculum']['difficulty']}&mode=adaptive")
assert adaptive["problem"] and adaptive["problem"]["curriculum"]["level"] == catalogue[0]["curriculum"]["level"]
assert adaptive["selection_mode"] == "adaptive"
assert_no_private_problem_fields(adaptive)
print("[PASS] Deterministic learner-scoped adaptive selection")
retry = send_json(f"{api}/sessions", "POST", {"problem_id": catalogue[0]["id"], "force_new": True}, 201)
assert retry["session_id"] != session_id and retry["current_attempt_id"] != session_attempt_id
assert_no_private_problem_fields(retry)
print("[PASS] Learner session privacy, persistence, completion and retry")
attempt = send_json(f"{api}/attempts", "POST", {"problem_id": catalogue[0]["id"]}, 201)
assert attempt["status"] == "draft" and attempt["revision"] == 0
solution = """On considère \\(x \\in \\mathbb{R}\\).

$$
f(x)=\\frac{x^2-1}{x+1}
$$

Pour \\(x\\neq-1\\), on obtient le résultat."""
saved = send_json(f"{api}/attempts/{attempt['id']}", "PATCH", {"solution_markdown": solution, "elapsed_seconds": 12, "expected_revision": 0})
assert saved["revision"] == 1 and get_json(f"{api}/attempts/{attempt['id']}")["solution_markdown"] == solution
assert send_json(f"{api}/attempts/{attempt['id']}", "PATCH", {"solution_markdown": "stale", "elapsed_seconds": 12, "expected_revision": 0}, 409)["error"] == "attempt_conflict"
submitted = send_json(f"{api}/attempts/{attempt['id']}/submit", "POST", {"expected_revision": 1})
assert submitted["status"] == "submitted" and "reference_solution" not in json.dumps(submitted)
assert send_json(f"{api}/attempts/{attempt['id']}", "PATCH", {"solution_markdown": "locked", "elapsed_seconds": 12, "expected_revision": 2}, 409)["error"] == "attempt_submitted"
print("[PASS] Attempt lifecycle, concurrency, and correction isolation")
with urlopen(frontend, timeout=10) as response:
    # The canonical application name is emitted in the page metadata and as the
    # accessible name of the brand lockup.
    assert "KHOLLELAB" in response.read().decode()
print("[PASS] Frontend reachable")
print("Smoke test passed.")
