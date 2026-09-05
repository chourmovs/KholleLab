from pathlib import Path
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app

settings.problems_dir = str(Path(__file__).resolve().parents[2] / 'problems')
settings.resources_dir = str(Path(__file__).resolve().parents[2] / 'resources')

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


def test_public_resource_catalogue_and_resolution_api():
    with TestClient(app) as client:
        catalogue = client.get('/api/resources?type=course&level=premiere&topic=derivatives')
        assert catalogue.status_code == 200
        assert catalogue.json()
        assert all(item['type'] == 'course' for item in catalogue.json())
        resource_id = catalogue.json()[0]['id']
        assert client.get(f'/api/resources/{resource_id}').json()['id'] == resource_id
        assert client.get('/api/resources/unknown-resource').status_code == 404

        resolved = client.get('/api/problems/premiere-derivatives-012/resources')
        assert resolved.status_code == 200
        assert resolved.json()['problem_id'] == 'premiere-derivatives-012'
        assert 0 < len(resolved.json()['resources']) <= 3
        assert 'reference_solution' not in resolved.text
        assert client.get('/api/problems/unknown-problem/resources').status_code == 404
