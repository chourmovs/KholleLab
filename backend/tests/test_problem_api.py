from pathlib import Path
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app

settings.problems_dir = str(Path(__file__).resolve().parents[2] / 'problems')

def test_public_problem_api_never_exposes_solution():
    with TestClient(app) as client:
        catalogue=client.get('/api/problems')
        assert catalogue.status_code == 200 and len(catalogue.json()) >= 5
        assert all('reference_solution' not in item for item in catalogue.json())
        identifier=catalogue.json()[0]['id']
        detail=client.get(f'/api/problems/{identifier}')
        assert detail.status_code == 200
        assert {'id','title','statement','hint_levels'} <= detail.json().keys()
        assert 'reference_solution' not in detail.json()
        assert client.get('/api/problems/does-not-exist').status_code == 404
        selection=client.get('/api/problems/select?level=terminale&difficulty=2')
        assert selection.status_code == 200
        assert selection.json()['problem']['curriculum']['level'] == 'terminale'
        assert 'reference_solution' not in selection.text
