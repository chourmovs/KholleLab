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
