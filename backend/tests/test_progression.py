from datetime import date, datetime, timedelta, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.api.attempts import session
from app.db.base import Base
from app.models.attempt import Attempt, AttemptStatus
from app.models.evaluation import Evaluation, EvaluationStage, EvaluationStatus
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.models.progression_event import ProgressionEvent, ProgressionEventType
from app.services.progression import (PROGRESSION_TIMEZONE, SESSION_COMPLETED_XP, XP_POLICY_VERSION,
                                      ProgressionService, grade_for_xp)
from test_session_api import Testing


def setup_function():
    Base.metadata.create_all(Testing.kw["bind"])
    with Testing.kw["bind"].begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    app.dependency_overrides[session] = lambda: Testing()


def completed(db, owner=None, solution="travail", when=None, status=LearningSessionStatus.COMPLETED,
              attempt_status=AttemptStatus.SUBMITTED):
    when = when or datetime.now(timezone.utc)
    learning = LearningSession(problem_id="test-problem", learner_id=owner or uuid.uuid4(), status=status,
                               completed_at=when if status == LearningSessionStatus.COMPLETED else None,
                               updated_at=when, active_problem_key=None)
    db.add(learning); db.flush()
    attempt = Attempt(problem_id=learning.problem_id, session_id=learning.id, status=attempt_status,
                      solution_markdown=solution, submitted_at=when if attempt_status == AttemptStatus.SUBMITTED else None)
    db.add(attempt); db.flush()
    return learning, attempt


def test_eligible_award_is_exactly_once_and_empty_or_abandoned_work_earns_nothing():
    with Testing() as db:
        valid, _ = completed(db)
        abandoned, _ = completed(db, status=LearningSessionStatus.ABANDONED)
        empty, _ = completed(db, solution="  ")
        draft, _ = completed(db, solution="saved", attempt_status=AttemptStatus.DRAFT)
        service = ProgressionService(db)
        first = service.ensure_completion_award(valid.id)
        second = service.ensure_completion_award(valid.id)
        assert first and second.id == first.id and first.xp == SESSION_COMPLETED_XP
        assert service.ensure_completion_award(abandoned.id) is None
        assert service.ensure_completion_award(empty.id) is None
        assert service.ensure_completion_award(draft.id) is None
        db.commit()
        assert db.scalar(select(func.sum(ProgressionEvent.xp))) == 10


def test_database_uniqueness_is_final_concurrent_award_guard():
    with Testing() as db:
        learning, _ = completed(db)
        values = dict(session_id=learning.id, event_type=ProgressionEventType.SESSION_COMPLETED, xp=10,
                      policy_version=XP_POLICY_VERSION, occurred_at=learning.completed_at,
                      activity_date=learning.completed_at.date())
        db.add(ProgressionEvent(**values)); db.commit()
        db.add(ProgressionEvent(**values))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.scalar(select(func.count(ProgressionEvent.id))) == 1


def test_grade_formula_boundaries():
    assert [(xp, grade_for_xp(xp)) for xp in (0, 49, 50, 149, 150, 299, 300, 500)] == [
        (0, 1), (49, 1), (50, 2), (149, 2), (150, 3), (299, 3), (300, 4), (500, 5)
    ]


def test_failed_incorrect_and_generated_evaluation_outcomes_never_change_practice_xp():
    with Testing() as db:
        failed_session, failed_attempt = completed(db)
        failed_session.problem_id = failed_attempt.problem_id = "llm-seconde-generated"
        incorrect_session, incorrect_attempt = completed(db)
        db.add_all([
            Evaluation(attempt_id=failed_attempt.id, status=EvaluationStatus.FAILED,
                       stage=EvaluationStage.FAILED, provider="fake", model="fake", prompt_version="v1"),
            Evaluation(attempt_id=incorrect_attempt.id, status=EvaluationStatus.COMPLETED,
                       stage=EvaluationStage.COMPLETED, verdict="incorrect", score=0,
                       provider="fake", model="fake", prompt_version="v1"),
        ])
        service = ProgressionService(db)
        assert service.ensure_completion_award(failed_session.id).xp == 10
        assert service.ensure_completion_award(incorrect_session.id).xp == 10
        db.commit()
        assert db.scalar(select(func.sum(ProgressionEvent.xp))) == 20


def test_distinct_day_streaks_gap_yesterday_grace_and_historical_longest():
    owner = uuid.uuid4(); today = date(2026, 9, 13)
    with Testing() as db:
        for offset in (9, 8, 7, 2, 1, 1):
            when = datetime.combine(today - timedelta(days=offset), datetime.min.time(), timezone.utc)
            learning, _ = completed(db, owner, when=when)
            ProgressionService(db).ensure_completion_award(learning.id)
        db.commit()
        value = ProgressionService(db).summary(owner, today=today)
        assert value["total_xp"] == 60 and value["completed_sessions"] == 6
        assert value["current_streak_days"] == 2 and not value["active_today"]
        assert value["longest_streak_days"] == 3
        assert value["last_active_date"] == today - timedelta(days=1)
        assert value["timezone"] == PROGRESSION_TIMEZONE
        assert ProgressionService(db).summary(owner, today=today + timedelta(days=2))["current_streak_days"] == 0


def submit_one(client, problem_id):
    learning = client.post("/api/sessions", json={"problem_id": problem_id}).json()
    attempt = learning["attempts"][0]
    saved = client.patch(f"/api/attempts/{attempt['id']}", json={
        "solution_markdown": "Une tentative réelle", "elapsed_seconds": 0, "expected_revision": 0,
    }).json()
    response = client.post(f"/api/attempts/{attempt['id']}/submit", json={"expected_revision": saved["revision"]})
    assert response.status_code == 200


def test_anonymous_claim_multi_device_and_logout_scope_progression(monkeypatch):
    monkeypatch.setattr("app.services.learner_identity.SessionLocal", Testing)
    with TestClient(app) as anonymous:
        ids = [item["id"] for item in anonymous.get("/api/problems").json()[:3]]
        for problem_id in ids: submit_one(anonymous, problem_id)
        assert anonymous.get("/api/progression").json()["total_xp"] == 30
        registered = anonymous.post("/api/auth/register", json={
            "email": "progress@example.com", "password": "progress-password",
            "display_name": "Ada", "claim_anonymous_history": True,
        })
        assert registered.status_code == 201
        assert anonymous.get("/api/progression").json()["total_xp"] == 30
        with Testing() as db:
            assert db.scalar(select(func.count(ProgressionEvent.id))) == 3
        with TestClient(app) as second_device:
            assert second_device.post("/api/auth/login", json={"email":"progress@example.com", "password":"progress-password"}).status_code == 200
            assert second_device.get("/api/progression").json()["total_xp"] == 30
        assert anonymous.post("/api/auth/logout").status_code == 204
        assert anonymous.get("/api/progression").json()["total_xp"] == 0


def test_complete_before_nonempty_submission_awards_when_attempt_later_arrives():
    with TestClient(app) as client:
        problem = client.get("/api/problems").json()[0]
        learning = client.post("/api/sessions", json={"problem_id":problem["id"]}).json()
        attempt = learning["attempts"][0]
        saved = client.patch(f"/api/attempts/{attempt['id']}", json={"solution_markdown":"réponse", "elapsed_seconds":1, "expected_revision":0}).json()
        assert client.post(f"/api/sessions/{learning['session_id']}/complete", json={}).status_code == 200
        assert client.get("/api/progression").json()["total_xp"] == 0
        assert client.post(f"/api/attempts/{attempt['id']}/submit", json={"expected_revision":saved["revision"]}).status_code == 200
        assert client.get("/api/progression").json()["total_xp"] == 10
