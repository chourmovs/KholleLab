from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_database(monkeypatch) -> None:
    monkeypatch.setattr("app.services.health.database_is_available", lambda: True)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "khollelab-api",
        "database": "ok",
    }


def test_health_fails_when_database_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.services.health.database_is_available", lambda: False)
    assert client.get("/api/health").status_code == 503

