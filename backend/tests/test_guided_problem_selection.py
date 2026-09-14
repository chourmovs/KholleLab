from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.attempts import session
from app.core.config import settings
from app.db.base import Base
from app.main import app
from app.models.attempt import Attempt
from app.models.curriculum_state import LearnerCurriculumState
from app.models.learning_session import LearningSession
from app.models.progression_event import ProgressionEvent
from app.services.evidence import EvidenceKind
from app.services.guided_problem import GuidedProblemService
from test_session_api import Testing

settings.problems_dir = str(Path(__file__).resolve().parents[2] / "problems")
settings.resources_dir = str(Path(__file__).resolve().parents[2] / "resources")


def setup_function():
    Base.metadata.create_all(Testing.kw["bind"])
    with Testing.kw["bind"].begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    app.dependency_overrides[session] = lambda: Testing()


def test_guided_requires_onboarding_and_rejects_manual_filters():
    with TestClient(app) as client:
        response = client.get("/api/problems/next")
        assert response.status_code == 409 and response.json()["detail"] == "onboarding_required"
        assert client.get("/api/problems/next?level=seconde").status_code == 422


def test_guided_is_deterministic_current_level_static_and_read_only():
    with TestClient(app) as client:
        client.put("/api/curriculum-progress/initial-level", json={"level": "seconde"})
        before = _side_effect_counts()
        first = client.get("/api/problems/next")
        second = client.get("/api/problems/next")
        assert first.status_code == second.status_code == 200
        assert first.json()["problem"]["id"] == second.json()["problem"]["id"]
        assert first.json()["problem"]["curriculum"]["level"] == "seconde"
        assert first.json()["target_difficulty"] == 2
        assert first.json()["candidate_pool"] == "unsolved"
        assert _side_effect_counts() == before


def test_active_work_wins_even_after_current_level_changes():
    with TestClient(app) as client:
        client.put("/api/curriculum-progress/initial-level", json={"level": "quatrieme"})
        problem_id = client.get("/api/problems/next").json()["problem"]["id"]
        active = client.post("/api/sessions", json={"problem_id": problem_id}).json()
        # Simulate a previously unlocked switch without modifying the protected draft.
        with Testing() as db:
            state = db.get(LearnerCurriculumState, _learner_id(db))
            state.current_level = "troisieme"
            db.commit()
        payload = client.get("/api/problems/next").json()
        assert payload["candidate_pool"] == "resume_active"
        assert payload["problem"]["id"] == problem_id
        assert client.get("/api/sessions/active/latest").json()["session_id"] == active["session_id"]


def test_explicit_advance_immediately_changes_guided_curriculum():
    with TestClient(app) as client:
        client.put("/api/curriculum-progress/initial-level", json={"level": "quatrieme"})
        with Testing() as db:
            state = db.get(LearnerCurriculumState, _learner_id(db))
            state.highest_unlocked_level = "troisieme"
            db.commit()
        advanced = client.post("/api/curriculum-progress/advance")
        assert advanced.status_code == 200
        assert advanced.json()["current_level"] == "troisieme"
        guided = client.get("/api/problems/next")
        assert guided.status_code == 200
        assert guided.json()["current_level"] == "troisieme"
        assert guided.json()["problem"]["curriculum"]["level"] == "troisieme"


def test_difficulty_v1_policy_is_conservative_and_bounded():
    class Item:
        def __init__(self, outcome, difficulty=3, level="seconde"):
            self.outcome, self.difficulty, self.level = outcome, difficulty, level
    class Context:
        recent_sessions = ()
    assert GuidedProblemService.resolve_target_difficulty(Context(), "seconde")[0] == 2
    for outcomes, expected in [
        ((EvidenceKind.POSITIVE, EvidenceKind.POSITIVE), 4),
        ((EvidenceKind.NEGATIVE, EvidenceKind.NEGATIVE), 2),
        ((EvidenceKind.POSITIVE, EvidenceKind.PARTIAL), 3),
    ]:
        Context.recent_sessions = tuple(Item(value) for value in outcomes)
        assert GuidedProblemService.resolve_target_difficulty(Context(), "seconde")[0] == expected
    Context.recent_sessions = (Item(EvidenceKind.POSITIVE, 5), Item(EvidenceKind.POSITIVE, 5))
    assert GuidedProblemService.resolve_target_difficulty(Context(), "seconde")[0] == 5
    Context.recent_sessions = (Item(EvidenceKind.NEGATIVE, 1), Item(EvidenceKind.NEGATIVE, 1))
    assert GuidedProblemService.resolve_target_difficulty(Context(), "seconde")[0] == 1
    Context.recent_sessions = (Item(EvidenceKind.POSITIVE, 4, "premiere"),)
    assert GuidedProblemService.resolve_target_difficulty(Context(), "seconde")[0] == 2


def test_guided_prioritizes_unsolved_units_then_keeps_variants_for_review():
    level = SimpleNamespace(value="quatrieme")
    family_1 = SimpleNamespace(id="family-f-v1", generation=SimpleNamespace(family_id="family-f"),
                               curriculum=SimpleNamespace(level=level))
    family_2 = SimpleNamespace(id="family-f-v2", generation=SimpleNamespace(family_id="family-f"),
                               curriculum=SimpleNamespace(level=level))
    standalone = SimpleNamespace(id="standalone-a", generation=None,
                                 curriculum=SimpleNamespace(level=level))
    candidates = [family_1, family_2, standalone]
    assert GuidedProblemService.unsolved_candidates(candidates, {"family:family-f"}) == [standalone]
    # With all units solved the caller falls back to the complete review pool.
    unsolved = GuidedProblemService.unsolved_candidates(
        candidates, {"family:family-f", "problem:standalone-a"})
    assert (unsolved or candidates) == candidates


def _side_effect_counts():
    with Testing() as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (LearningSession, Attempt, ProgressionEvent))


def _learner_id(db):
    return db.scalar(select(LearnerCurriculumState.learner_id))
