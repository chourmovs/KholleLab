from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_demo_problem_is_available() -> None:
    response = client.get("/api/v1/problems/demo-001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "demo-001"
    assert payload["difficulty"] == 2
    assert "algèbre" in payload["topics"]


def test_unknown_problem_returns_404() -> None:
    response = client.get("/api/v1/problems/does-not-exist")

    assert response.status_code == 404
