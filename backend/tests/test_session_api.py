import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.attempts import session
from app.db.base import Base
from app.main import app
import app.models as models  # noqa: F401

engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
Testing=sessionmaker(bind=engine,expire_on_commit=False)
Base.metadata.create_all(engine)


def setup_function():
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables): connection.execute(table.delete())
    app.dependency_overrides[session]=lambda: Testing()


def test_session_lifecycle_restore_history_and_retry():
    with TestClient(app) as client:
        problem=client.get("/api/problems").json()[0]
        first=client.post("/api/sessions",json={"problem_id":problem["id"]})
        assert first.status_code==201
        value=first.json(); session_id=value["session_id"]; attempt=value["attempts"][0]
        duplicate=client.post("/api/sessions",json={"problem_id":problem["id"]}).json()
        assert duplicate["session_id"]==session_id and duplicate["number_of_attempts"]==1
        saved=client.patch(f"/api/attempts/{attempt['id']}",json={"solution_markdown":"Une preuve durable","elapsed_seconds":42,"expected_revision":0}).json()
        restored=client.get("/api/sessions/active/latest").json()
        assert restored["session_id"]==session_id and restored["final_work"]=="Une preuve durable" and restored["duration_seconds"]==42
        submitted=client.post(f"/api/attempts/{attempt['id']}/submit",json={"expected_revision":saved["revision"]})
        assert submitted.status_code==200
        detail=client.get(f"/api/sessions/{session_id}").json()
        assert detail["status"]=="completed" and detail["completed_at"] and detail["final_work"]=="Une preuve durable"
        assert client.get("/api/sessions/active/latest").json() is None
        retry=client.post("/api/sessions",json={"problem_id":problem["id"],"force_new":True}).json()
        assert retry["session_id"]!=session_id
        history=client.get("/api/sessions").json()
        assert [x["session_id"] for x in history][:2]==[retry["session_id"],session_id]
        assert client.post(f"/api/sessions/{retry['session_id']}/abandon",json={"expected_status":"active"}).json()["status"]=="abandoned"


def test_missing_problem_and_unknown_session_are_safe():
    from app.models.learning_session import LearningSession, LearningSessionStatus
    with Testing() as db:
        missing=LearningSession(problem_id="legacy-deleted",status=LearningSessionStatus.COMPLETED)
        db.add(missing);db.commit();identifier=missing.id
    with TestClient(app) as client:
        value=client.get(f"/api/sessions/{identifier}")
        assert value.status_code==404
        assert client.get("/api/sessions").json() == []
        assert client.get(f"/api/sessions/{uuid.uuid4()}").status_code==404


def assert_no_private_problem_fields(value):
    if isinstance(value, dict):
        assert "reference_solution" not in value
        for child in value.values(): assert_no_private_problem_fields(child)
    elif isinstance(value, list):
        for child in value: assert_no_private_problem_fields(child)


def test_privacy_isolation_terminal_immutability_and_retry():
    with TestClient(app) as learner_a, TestClient(app) as learner_b:
        problem=learner_a.get("/api/problems").json()[0]
        first=learner_a.post("/api/sessions",json={"problem_id":problem["id"]}).json(); assert_no_private_problem_fields(first)
        other=learner_b.post("/api/sessions",json={"problem_id":problem["id"]}).json()
        assert other["session_id"] != first["session_id"]
        for method,path in (("get",f"/api/sessions/{first['session_id']}"),("post",f"/api/sessions/{first['session_id']}/complete"),("post",f"/api/sessions/{first['session_id']}/abandon")):
            response=learner_b.post(path,json={}) if method=="post" else learner_b.get(path)
            assert response.status_code==404 and response.json()["error"]=="session_not_found"
        assert_no_private_problem_fields(learner_a.get("/api/sessions").json())
        assert_no_private_problem_fields(learner_a.get("/api/sessions/active/latest").json())
        attempt=first["attempts"][0]
        submitted=learner_a.post(f"/api/attempts/{attempt['id']}/submit",json={"expected_revision":0})
        assert submitted.status_code==200
        assert learner_a.post(f"/api/sessions/{first['session_id']}/abandon",json={}).status_code==409
        retry=learner_a.post("/api/sessions",json={"problem_id":problem["id"],"force_new":True}).json()
        assert retry["session_id"] != first["session_id"] and retry["current_attempt_id"] != first["current_attempt_id"]
        assert retry["attempts"][0]["id"] == retry["current_attempt_id"]


def test_adaptive_selection_is_learner_scoped_and_private():
    with TestClient(app) as learner_a, TestClient(app) as learner_b:
        baseline = learner_b.get("/api/problems/select?level=seconde&difficulty=2&mode=adaptive").json()
        assert baseline["selection_mode"] == "adaptive" and baseline.get("adaptation") is None
        first_id = baseline["problem"]["id"]
        learning = learner_a.post("/api/sessions", json={"problem_id": first_id}).json()
        learner_a.post(f"/api/sessions/{learning['session_id']}/complete", json={})

        adapted = learner_a.get("/api/problems/select?level=seconde&difficulty=2&mode=adaptive").json()
        isolated = learner_b.get("/api/problems/select?level=seconde&difficulty=2&mode=adaptive").json()
        assert adapted["problem"]["id"] != first_id
        assert "recent_problem_avoidance" in adapted["adaptation"]["reason_codes"]
        assert isolated["problem"]["id"] == first_id and isolated.get("adaptation") is None
        assert_no_private_problem_fields(adapted)
        assert "learner_id" not in str(adapted)


def test_history_pagination_validation_and_legacy_isolation():
    with TestClient(app) as client:
        assert client.get("/api/sessions?limit=101").status_code==422
        assert client.get("/api/sessions?offset=-1").status_code==422
