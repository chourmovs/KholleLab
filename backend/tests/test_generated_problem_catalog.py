import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
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
from app.services.adaptive_context import AdaptiveContextBuilder
from app.services.learner_profile import LearnerProfileBuilder
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
        llm_problem_max_generation_attempts=3,
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


@pytest.mark.asyncio
async def test_pool_grows_to_target_then_recycles_least_recently_seen(catalogue):
    catalog, curriculum, sessions = catalogue
    provider = Provider()
    service = ProblemGenerationService(catalog, curriculum, provider, config(
        llm_problem_pool_target=4, llm_problem_near_duplicate_threshold=1))
    learner = uuid.uuid4()
    created = []
    with sessions() as db:
        for index in range(4):
            problem, reused = await service.select(db=db, learner_id=learner, level="seconde",
                expectation_id=EXPECTATION, difficulty=2, domain="algebra")
            assert not reused
            created.append(problem)
            db.add(LearningSession(problem_id=problem.id, learner_id=learner,
                updated_at=datetime.now(timezone.utc) + timedelta(minutes=index)))
            db.commit()
        assert provider.generator_calls == provider.critic_calls == 4

        recycled, reused = await service.select(db=db, learner_id=learner, level="seconde",
            expectation_id=EXPECTATION, difficulty=2, domain="algebra")
        assert reused and recycled.id == created[0].id
        assert provider.generator_calls == provider.critic_calls == 4


@pytest.mark.asyncio
async def test_unseen_shared_stock_always_saves_both_llm_calls(catalogue):
    catalog, curriculum, sessions = catalogue
    builder = ProblemGenerationService(catalog, curriculum, Provider(), config(
        llm_problem_pool_target=3, llm_problem_near_duplicate_threshold=1))
    source_learner = uuid.uuid4()
    with sessions() as db:
        stock = []
        for _ in range(3):
            problem, _ = await builder.select(db=db, learner_id=source_learner, level="seconde",
                expectation_id=EXPECTATION, difficulty=3, domain="algebra")
            stock.append(problem)
            db.add(LearningSession(problem_id=problem.id, learner_id=source_learner)); db.commit()

        learner = uuid.uuid4()
        db.add(LearningSession(problem_id=stock[0].id, learner_id=learner)); db.commit()
        provider = Provider()
        selected, reused = await ProblemGenerationService(catalog, curriculum, provider, config(
            llm_problem_pool_target=3)).select(db=db, learner_id=learner, level="seconde",
                expectation_id=EXPECTATION, difficulty=3, domain="algebra")
        assert reused and selected.id == stock[1].id
        assert provider.generator_calls == provider.critic_calls == 0


@pytest.mark.asyncio
async def test_prerequisites_and_distinct_model_provenance(catalogue):
    catalog, curriculum, sessions = catalogue
    with sessions() as db:
        problem, _ = await ProblemGenerationService(catalog, curriculum, Provider(), config()).select(
            db=db, learner_id=uuid.uuid4(), level="premiere",
            expectation_id="lycee-2026-1re-derivative", difficulty=2, domain="analysis")
        assert problem.prerequisites == ("function-variation",)
        assert "derivatives" not in problem.prerequisites
        row = db.get(GeneratedProblem, problem.id)
        assert row.generator_model != row.critic_model
        assert "Qwen" in row.generator_model and "gemma" in row.critic_model


@pytest.mark.asyncio
async def test_cross_bucket_exact_duplicate_regenerates(catalogue):
    catalog, curriculum, sessions = catalogue
    with sessions() as db:
        first_provider = Provider()
        await ProblemGenerationService(catalog, curriculum, first_provider, config()).select(
            db=db, learner_id=uuid.uuid4(), level="seconde", expectation_id=EXPECTATION,
            difficulty=2, domain="algebra")
        second_provider = Provider()
        second, reused = await ProblemGenerationService(catalog, curriculum, second_provider, config(
            llm_problem_near_duplicate_threshold=1)).select(
            db=db, learner_id=uuid.uuid4(), level="seconde", expectation_id=EXPECTATION,
            difficulty=3, domain="algebra")
        assert not reused and second_provider.generator_calls == 2
        assert second_provider.critic_calls == 1
        assert db.scalar(select(GeneratedProblem).where(GeneratedProblem.difficulty == 3)).id == second.id
        assert len(list(db.scalars(select(GeneratedProblem)))) == 2


@pytest.mark.asyncio
async def test_concurrent_empty_bucket_runs_one_pipeline(catalogue):
    catalog, curriculum, sessions = catalogue
    provider = Provider()
    service = ProblemGenerationService(catalog, curriculum, provider, config())
    async def request():
        with sessions() as db:
            return await service.select(db=db, learner_id=uuid.uuid4(), level="seconde",
                expectation_id=EXPECTATION, difficulty=5, domain="algebra")
    results = await asyncio.gather(request(), request())
    assert results[0][0].id == results[1][0].id
    assert provider.generator_calls == provider.critic_calls == 1


@pytest.mark.asyncio
async def test_generated_history_is_batch_resolved_for_adaptation_and_profile(catalogue):
    catalog, curriculum, sessions = catalogue
    learner = uuid.uuid4()
    with sessions() as db:
        problem, _ = await ProblemGenerationService(catalog, curriculum, Provider(), config()).select(
            db=db, learner_id=learner, level="premiere",
            expectation_id="lycee-2026-1re-derivative", difficulty=4, domain="analysis")
        for offset in range(3):
            db.add(LearningSession(problem_id=problem.id, learner_id=learner,
                status="completed", completed_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc) + timedelta(minutes=offset)))
        db.commit()

        context = AdaptiveContextBuilder().build(db, learner, catalog)
        item = context.recent_sessions[0]
        assert item.topics and item.skills
        assert item.prerequisites == ("function-variation",)
        assert item.difficulty == 4 and item.family_id == "produit-nul"

        statements = []
        from sqlalchemy import event
        def capture(_conn, _cursor, statement, _parameters, _context, _many):
            if "generated_problems" in statement and statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)
        event.listen(db.get_bind(), "before_cursor_execute", capture)
        try:
            profile = LearnerProfileBuilder(db, catalog).build(learner)
        finally:
            event.remove(db.get_bind(), "before_cursor_execute", capture)
        assert profile["evidence_window"]["sessions_considered"] == 3
        assert any(item.identifier == "analysis" for item in profile["topics"])
        assert len(statements) == 1


def test_concurrent_serve_counter_has_no_lost_updates(catalogue, tmp_path):
    source_catalog, _curriculum, _sessions = catalogue
    engine = create_engine(f"sqlite:///{tmp_path / 'counter.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    catalog = ProblemCatalog(source_catalog.static, sessions)
    # The generated row is inserted directly so this test only observes serving SQL.
    from app.domain.problem import CurriculumInfo, Problem, Skill, SourceInfo, Topic
    payload = Problem(id="llm-counter", title="Counter", statement="Calculer 1+1.",
        reference_solution="2", curriculum=CurriculumInfo(level="seconde", difficulty=1),
        topics=(Topic.ARITHMETIC,), skills=(Skill.REASONING,), source=SourceInfo(type="llm", name="test"))
    row = GeneratedProblem(id=payload.id, content_hash="a" * 64, statement_hash="b" * 64,
        status=GeneratedProblemStatus.ACCEPTED, payload_json=payload.model_dump(mode="json"), level="seconde",
        programme_id="p", expectation_id="e", domain="numbers", difficulty=1,
        generator_family="qwen", generator_model="g", generator_prompt_version="v",
        critic_family="gemma", critic_model="c", critic_prompt_version="v",
        validation_version="v", validation_json={})
    with sessions() as db:
        db.add(row); db.commit()
    def serve():
        with sessions() as db:
            catalog.mark_served(row.id, db)
            db.commit()
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: serve(), range(24)))
    with sessions() as db:
        assert db.get(GeneratedProblem, row.id).usage_count == 24
