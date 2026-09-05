from pathlib import Path
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app
settings.problems_dir = str(Path(__file__).resolve().parents[2] / 'problems')

def test_health_reports_database_and_corpus(monkeypatch):
    monkeypatch.setattr('app.services.health.database_is_available', lambda: True)
    with TestClient(app) as client:
        body=client.get('/api/health').json()
    assert body == {'status':'ok','service':'khollelab-api','database':'ok','problem_corpus':'ok','problem_count':50,'curriculum_levels':5,'inference':'disabled'}

def test_health_fails_when_database_is_unavailable(monkeypatch):
    monkeypatch.setattr('app.services.health.database_is_available', lambda: False)
    with TestClient(app) as client: assert client.get('/api/health').status_code == 503

def test_remote_inference_status_is_non_billable_configuration_state(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "fake")
    with TestClient(app) as client:
        inference = client.get('/api/inference/status').json()
    assert inference["status"] == "disabled"
    assert inference["family"] == "qwen"
    assert inference["fast_backend"] == "nscale"
    assert inference["deep_backend"] == "nscale"

def test_ready_inference_reason_none_serializes(monkeypatch):
    async def ready(**_):
        return {"provider":"huggingface","status":"ready","family":"qwen","fast_model":"Qwen3-8B","fast_backend":"nscale","deep_model":"Qwen3-32B","deep_backend":"nscale","reason":None,"latency_ms":123.4,"checks":{}}
    monkeypatch.setattr("app.api.routes.diagnose",ready)
    with TestClient(app) as client:
        response=client.get("/api/inference/status")
    assert response.status_code==200
    assert response.json()["reason"] is None
    assert response.json()["latency_ms"]==123.4

def test_health_survives_diagnostic_exception(monkeypatch):
    monkeypatch.setattr('app.services.health.database_is_available', lambda: True)
    async def broken(**_): raise RuntimeError("diagnostic exploded")
    monkeypatch.setattr("app.api.routes.diagnose",broken)
    with TestClient(app) as client:
        response=client.get("/api/health")
    assert response.status_code==200
    assert response.json()["inference"]=="error"
