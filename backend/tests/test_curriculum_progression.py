from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.attempts import session
from app.db.base import Base
from app.domain.problem import CURRICULUM_ORDER
from app.main import app
from app.models.attempt import Attempt, AttemptStatus
from app.models.curriculum_state import LearnerCurriculumState
from app.models.evaluation import Evaluation, EvaluationStage, EvaluationStatus
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.services.authentication import claim_anonymous_history
from app.services.curriculum_progression import (CurriculumProgressionService,
                                                 LockedCurriculumLevel,
                                                 NEXT_LEVEL_UNLOCK_RATIO)
from test_session_api import Testing


class Corpus:
    def __init__(self, counts):
        self.items = [SimpleNamespace(id=f"{level}-{index}", curriculum=SimpleNamespace(
            level=SimpleNamespace(value=level))) for level, count in counts.items() for index in range(count)]

    def list_static(self):
        return self.items

    def list(self):
        return self.items

    def get_many(self, identifiers, db=None):
        wanted = set(identifiers)
        return {item.id: item for item in self.items if item.id in wanted}


def setup_function():
    Base.metadata.create_all(Testing.kw["bind"])
    with Testing.kw["bind"].begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    app.dependency_overrides[session] = lambda: Testing()


def observation(db, owner, problem_id, *, verdict="correct", confidence=.9,
                evaluation_status=EvaluationStatus.COMPLETED,
                session_status=LearningSessionStatus.COMPLETED):
    now = datetime.now(timezone.utc)
    learning = LearningSession(problem_id=problem_id, learner_id=owner, status=session_status,
                               active_problem_key=None, updated_at=now,
                               completed_at=now if session_status == LearningSessionStatus.COMPLETED else None)
    db.add(learning); db.flush()
    attempt = Attempt(problem_id=problem_id, session_id=learning.id, status=AttemptStatus.SUBMITTED,
                      solution_markdown="solution", submitted_at=now)
    db.add(attempt); db.flush()
    evaluation = Evaluation(attempt_id=attempt.id, status=evaluation_status,
                            stage=EvaluationStage.COMPLETED if evaluation_status == EvaluationStatus.COMPLETED else EvaluationStage.FAILED,
                            verdict=verdict, confidence=confidence, provider="fake", model="fake",
                            prompt_version="test")
    db.add(evaluation); db.flush()
    return learning


def test_new_and_legacy_learners_are_lazily_bootstrapped_once_from_recent_history():
    owner = uuid.uuid4(); corpus = Corpus({level: 2 for level in CURRICULUM_ORDER})
    with Testing() as db:
        observation(db, owner, "seconde-0", verdict="incorrect")
        service = CurriculumProgressionService(db, corpus)
        first = service.get_or_create_state(owner)
        second = service.get_or_create_state(owner)
        assert first is second
        assert (first.initial_level, first.current_level, first.highest_unlocked_level) == ("seconde",) * 3
        assert first.onboarding_completed is False
        assert len(list(db.scalars(select(LearnerCurriculumState)))) == 1


@pytest.mark.parametrize("verdict,confidence,status,session_status,expected", [
    ("correct", .9, EvaluationStatus.COMPLETED, LearningSessionStatus.COMPLETED, 1),
    ("mostly_correct", .9, EvaluationStatus.COMPLETED, LearningSessionStatus.COMPLETED, 1),
    ("partial", .9, EvaluationStatus.COMPLETED, LearningSessionStatus.COMPLETED, 0),
    ("incorrect", .9, EvaluationStatus.COMPLETED, LearningSessionStatus.COMPLETED, 0),
    ("correct", .64, EvaluationStatus.COMPLETED, LearningSessionStatus.COMPLETED, 0),
    ("correct", .9, EvaluationStatus.FAILED, LearningSessionStatus.COMPLETED, 0),
    ("correct", .9, EvaluationStatus.COMPLETED, LearningSessionStatus.ABANDONED, 0),
])
def test_success_uses_shared_evidence_semantics(verdict, confidence, status, session_status, expected):
    owner = uuid.uuid4(); corpus = Corpus({"quatrieme": 2})
    with Testing() as db:
        observation(db, owner, "quatrieme-0", verdict=verdict, confidence=confidence,
                    evaluation_status=status, session_status=session_status)
        assert CurriculumProgressionService(db, corpus).level_progress(owner, "quatrieme")["solved"] == expected


def test_unique_success_is_permanent_across_duplicate_and_later_failed_observations():
    owner = uuid.uuid4(); corpus = Corpus({"quatrieme": 2})
    with Testing() as db:
        observation(db, owner, "quatrieme-0", verdict="incorrect")
        observation(db, owner, "quatrieme-0")
        observation(db, owner, "quatrieme-0")
        observation(db, owner, "quatrieme-0", verdict="incorrect")
        value = CurriculumProgressionService(db, corpus).level_progress(owner, "quatrieme")
        assert value == {"level":"quatrieme", "eligible":2, "solved":1,
                         "progress":.5, "progress_percent":50.0}


@pytest.mark.parametrize("solved,unlocked", [(59, False), (60, True), (61, True)])
def test_unlock_boundary_is_canonical_and_does_not_auto_promote(solved, unlocked):
    owner = uuid.uuid4(); corpus = Corpus({"quatrieme": 100, "troisieme": 1})
    with Testing() as db:
        for index in range(solved): observation(db, owner, f"quatrieme-{index}")
        service = CurriculumProgressionService(db, corpus)
        state = service.refresh_unlocks(owner)
        assert NEXT_LEVEL_UNLOCK_RATIO == .60
        assert (state.highest_unlocked_level == "troisieme") is unlocked
        assert state.current_level == "quatrieme"


def test_unlock_is_permanent_switch_is_gated_and_final_empty_levels_are_safe():
    owner = uuid.uuid4(); corpus = Corpus({"quatrieme": 5, "troisieme": 0})
    with Testing() as db:
        service = CurriculumProgressionService(db, corpus)
        with pytest.raises(LockedCurriculumLevel): service.set_current_level(owner, "troisieme")
        for index in range(3): observation(db, owner, f"quatrieme-{index}")
        assert service.refresh_unlocks(owner).highest_unlocked_level == "troisieme"
        service.set_current_level(owner, "troisieme")
        corpus.items.extend(Corpus({"quatrieme": 10}).items)
        state = service.refresh_unlocks(owner)
        assert state.highest_unlocked_level == state.current_level == "troisieme"
        assert service.level_progress(owner, "troisieme")["progress"] == 0

        final_owner = uuid.uuid4()
        final = service.set_initial_level(final_owner, CURRICULUM_ORDER[-1])
        assert service.refresh_unlocks(final_owner).highest_unlocked_level == CURRICULUM_ORDER[-1]


def test_curriculum_state_follows_identity_claim_without_copying_history():
    anonymous, account = uuid.uuid4(), uuid.uuid4(); corpus = Corpus({"quatrieme": 2})
    with Testing() as db:
        service = CurriculumProgressionService(db, corpus)
        service.set_initial_level(anonymous, "quatrieme")
        observation(db, anonymous, "quatrieme-0")
        assert claim_anonymous_history(db, anonymous, account) == 1
        db.commit()
        state = db.get(LearnerCurriculumState, account)
        assert state and state.onboarding_completed
        assert service.level_progress(account, "quatrieme")["solved"] == 1


def test_anonymous_api_initial_level_is_idempotent_and_rejects_locked_switch():
    with TestClient(app) as client:
        first = client.get("/api/curriculum-progress")
        assert first.status_code == 200 and first.json()["current_level"] == CURRICULUM_ORDER[0]
        chosen = client.put("/api/curriculum-progress/initial-level", json={"level":"seconde"})
        assert chosen.status_code == 200 and chosen.json()["onboarding_completed"] is True
        again = client.put("/api/curriculum-progress/initial-level", json={"level":"seconde"})
        assert again.status_code == 200
        assert client.put("/api/curriculum-progress/current-level", json={"level":"premiere"}).status_code == 409
        assert client.put("/api/curriculum-progress/initial-level", json={"level":"premiere"}).status_code == 409
