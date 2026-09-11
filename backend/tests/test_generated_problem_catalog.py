import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.generated_problem import GeneratedProblem, GeneratedProblemStatus
from app.models.learning_session import LearningSession
from app.schemas.problem_generation import GeneratedProblemDraft, ProblemGenerationCriticResult
from app.services.curriculum_repository import CurriculumRepository
from app.services.problem_catalog import ProblemCatalog
from app.services.problem_generation import ProblemGenerationService
from app.services.problem_repository import ProblemRepository

ROOT = Path(__file__).resolve().parents[2]
EXPECTATION = "lycee-2026-2de-factorisation"


class Provider:
    name = "fake"
    model = "deterministic-generator"

    def __init__(self, rejects=0):
        self.generator_calls = self.critic_calls = 0
        self.rejects = rejects

    async def structured_response(self, *, response_model, **_):
        if response_model is GeneratedProblemDraft:
            self.generator_calls += 1
            n = self.generator_calls
            return GeneratedProblemDraft(title=f"Factorisation raisonnée {n}",
                statement=f"Sans développer, factoriser puis résoudre (x-{10+n})(x+{20+n})=0 et justifier les solutions.",
                reference_solution=f"Le produit est nul si x={10+n} ou x=-{20+n}. La propriété du produit nul justifie la réciproque.",
                hints=("Utiliser la propriété du produit nul.",), estimated_minutes=10, archetype="produit-nul")
        self.critic_calls += 1
        accepted = self.critic_calls > self.rejects
        return ProblemGenerationCriticResult(mathematical_correctness=accepted,
            reference_solution_correctness=accepted, well_posed=True, level_appropriate=True,
            curriculum_aligned=True, difficulty_plausible=True, unambiguous=True,
            no_answer_leakage=True, issue_codes=() if accepted else ("incorrect",))


@pytest.fixture
def catalogue():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    curriculum = CurriculumRepository(ROOT / "curriculum"); curriculum.load()
    static = ProblemRepository(ROOT / "problems", curriculum, "2026-2027"); static.load()
    return ProblemCatalog(static, sessions), curriculum, sessions


def config(**values):
    defaults = dict(llm_problem_generation_enabled=True, llm_problem_pool_target=8,
        llm_problem_pool_min_available=2, llm_problem_max_generation_attempts=3,
        llm_problem_diversity_context_limit=8, llm_problem_near_duplicate_threshold=.95,
        llm_problem_generator_family=SimpleNamespace(value="qwen"),
        llm_problem_critic_family=SimpleNamespace(value="gemma"))
    return SimpleNamespace(**(defaults | values))


@pytest.mark.asyncio
async def test_cross_learner_global_reuse_saves_both_llm_passes(catalogue):
    catalog, curriculum, sessions = catalogue
    provider = Provider(); service = ProblemGenerationService(catalog, curriculum, provider, config())
    with sessions() as db:
        first, reused = await service.select(db=db, learner_id=uuid.uuid4(), level="seconde",
            expectation_id=EXPECTATION, difficulty=2, domain="algebra")
        assert not reused and provider.generator_calls == provider.critic_calls == 1
        second, reused = await service.select(db=db, learner_id=uuid.uuid4(), level="seconde",
            expectation_id=EXPECTATION, difficulty=2, domain="algebra")
        assert reused and second.id == first.id
        assert provider.generator_calls == provider.critic_calls == 1
        row = db.scalar(select(GeneratedProblem)); assert row.usage_count == 2
        assert not hasattr(row, "learner_id") and not hasattr(row, "session_id")


@pytest.mark.asyncio
async def test_unseen_is_preferred_and_critic_rejection_is_bounded(catalogue):
    catalog, curriculum, sessions = catalogue
    provider = Provider(rejects=1); service = ProblemGenerationService(catalog, curriculum, provider, config())
    learner = uuid.uuid4()
    with sessions() as db:
        first, _ = await service.select(db=db, learner_id=learner, level="seconde",
            expectation_id=EXPECTATION, difficulty=3, domain="algebra")
        assert provider.generator_calls == provider.critic_calls == 2
        db.add(LearningSession(problem_id=first.id, learner_id=learner)); db.commit()
        other_provider = Provider(); other = ProblemGenerationService(catalog, curriculum, other_provider, config())
        second, reused = await other.select(db=db, learner_id=uuid.uuid4(), level="seconde",
            expectation_id=EXPECTATION, difficulty=3, domain="algebra")
        assert reused and second.id == first.id and other_provider.generator_calls == 0


@pytest.mark.asyncio
async def test_retired_resolves_for_history_but_is_never_selected(catalogue):
    catalog, curriculum, sessions = catalogue
    service = ProblemGenerationService(catalog, curriculum, Provider(), config())
    with sessions() as db:
        problem, _ = await service.select(db=db, learner_id=uuid.uuid4(), level="seconde",
            expectation_id=EXPECTATION, difficulty=4, domain="algebra")
        row = db.get(GeneratedProblem, problem.id); row.status = GeneratedProblemStatus.RETIRED; db.commit()
        assert catalog.get(problem.id).id == problem.id
        assert catalog.find_generated(programme_id=row.programme_id, level="seconde",
            expectation_id=EXPECTATION, difficulty=4, db=db) == []
        assert "reference_solution" not in problem.model_dump(exclude={"reference_solution"})
