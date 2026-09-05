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

def test_local_inference_loading_is_a_non_blocking_starting_state(monkeypatch):
    class LoadingClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url):
            import httpx
            return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(settings, "llm_provider", "local")
    monkeypatch.setattr("app.api.routes.httpx.AsyncClient", lambda **kwargs: LoadingClient())
    monkeypatch.setattr('app.services.health.database_is_available', lambda: True)
    with TestClient(app) as client:
        inference = client.get('/api/inference/status').json()
        health_body = client.get('/api/health').json()
    assert inference == {
        'provider': 'local', 'status': 'starting', 'model': 'Qwen3-4B',
        'quantization': 'Q4_K_M', 'backend': 'llama.cpp',
        'reason': 'model_loading', 'latency_ms': inference['latency_ms'],
    }
    assert health_body['status'] == 'ok'
    assert health_body['inference'] == 'starting'
