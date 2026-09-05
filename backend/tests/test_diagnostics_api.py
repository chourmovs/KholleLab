from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def configure(monkeypatch, tmp_path, *, enabled=True):
    monkeypatch.setattr(settings, "diagnostics_enabled", enabled)
    monkeypatch.setattr(settings, "diagnostics_token", "correct-horse-battery-staple")
    monkeypatch.setattr(settings, "runtime_logs_dir", str(tmp_path))


def test_diagnostics_disabled_is_hidden(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, enabled=False)
    with TestClient(app) as client:
        assert client.get("/api/diagnostics/logs?source=application", headers={"X-Diagnostics-Token": "correct-horse-battery-staple"}).status_code == 404


def test_diagnostics_rejects_bad_token(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/diagnostics/logs?source=application", headers={"X-Diagnostics-Token": "wrong"}).status_code == 401


def test_log_sources_are_fixed_and_tail_is_bounded(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    (tmp_path / "khollelab.log").write_text("\n".join(f"line-{n}" for n in range(600)))
    (tmp_path / "llama.log").write_text("model loaded\n")
    headers = {"X-Diagnostics-Token": "correct-horse-battery-staple"}
    with TestClient(app) as client:
        application = client.get("/api/diagnostics/logs?source=application&lines=500", headers=headers)
        inference = client.get("/api/diagnostics/logs?source=inference&lines=200", headers=headers)
        assert application.status_code == 200
        assert len(application.json()["lines"]) == 500
        assert application.json()["lines"][0] == "line-101"
        assert inference.json()["lines"] == ["model loaded"]
        assert client.get("/api/diagnostics/logs?source=../secret", headers=headers).status_code == 422
        assert client.get("/api/diagnostics/logs?source=/etc/passwd", headers=headers).status_code == 422
        assert client.get("/api/diagnostics/logs?source=application&lines=501", headers=headers).status_code == 422
