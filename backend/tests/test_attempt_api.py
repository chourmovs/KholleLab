import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.api.attempts import session
from app.db.base import Base
from app.main import app
from app.models.attempt import Attempt  # noqa: F401

engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
Testing=sessionmaker(bind=engine,expire_on_commit=False)
Base.metadata.create_all(engine)
app.dependency_overrides[session]=lambda: Testing()

def test_attempt_lifecycle_and_conflicts():
    with TestClient(app) as client:
        problem=client.get("/api/problems").json()[0]["id"]
        response=client.post("/api/attempts",json={"problem_id":problem});assert response.status_code==201
        attempt=response.json();assert attempt["revision"]==0 and attempt["status"]=="draft" and "reference_solution" not in json.dumps(attempt)
        attempt_id=attempt["id"]
        assert client.get(f"/api/attempts/{attempt_id}").status_code==200
        denied=client.get(f"/api/attempts/{attempt_id}/reference-solution")
        assert denied.status_code==409 and denied.json()["error"]=="attempt_not_submitted"
        saved=client.patch(f"/api/attempts/{attempt_id}",json={"solution_markdown":"On pose $x^2$.","elapsed_seconds":2,"expected_revision":0});assert saved.status_code==200 and saved.json()["revision"]==1
        assert client.patch(f"/api/attempts/{attempt_id}",json={"solution_markdown":"stale","elapsed_seconds":2,"expected_revision":0}).status_code==409
        submitted=client.post(f"/api/attempts/{attempt_id}/submit",json={"expected_revision":1});assert submitted.status_code==200 and submitted.json()["status"]=="submitted"
        correction=client.get(f"/api/attempts/{attempt_id}/reference-solution")
        assert correction.status_code==200 and correction.json()["reference_solution"]
        assert client.patch(f"/api/attempts/{attempt_id}",json={"solution_markdown":"no","elapsed_seconds":2,"expected_revision":2}).status_code==409
        assert client.post(f"/api/attempts/{attempt_id}/submit",json={"expected_revision":2}).status_code==409

def test_attempt_validation_and_missing_problem():
    with TestClient(app) as client:
        assert client.post("/api/attempts",json={"problem_id":"missing"}).status_code==404
        assert client.get("/api/attempts/not-a-uuid").status_code==422
        import uuid
        missing=client.get(f"/api/attempts/{uuid.uuid4()}/reference-solution")
        assert missing.status_code==404 and missing.json()["error"]=="attempt_not_found"
        problem=client.get("/api/problems").json()[0]["id"]
        attempt=client.post("/api/attempts",json={"problem_id":problem}).json()
        url=f"/api/attempts/{attempt['id']}"
        assert client.patch(url,json={"solution_markdown":"x","elapsed_seconds":-1,"expected_revision":0}).status_code==422
        assert client.patch(url,json={"solution_markdown":"x"*100001,"elapsed_seconds":0,"expected_revision":0}).status_code==422
