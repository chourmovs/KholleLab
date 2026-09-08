from pathlib import Path

import pytest
import yaml

from app.domain.problem import CurriculumLevel, Skill, Topic
from app.services.problem_repository import ProblemRepository
from app.services.resource_repository import (
    ResourceCorpusError,
    ResourceRepository,
    validate_problem_resource_refs,
    validate_resource_curriculum_refs,
)
from app.services.curriculum_repository import CurriculumRepository
from app.services.resource_resolver import (EXPECTATION_WEIGHT, EXPLICIT_REF_WEIGHT,
                                             KNOWLEDGE_WEIGHT, ResourceContext,
                                             ResourceResolver, context_for_problem)
from app.services.tutor import select_resource
from app.schemas.tutor import ResourceNeed, TutorTrigger
from types import SimpleNamespace


def resource(kind="course", identifier="course-item", **overrides):
    value = {
        "id": identifier,
        "type": kind,
        "title": "Ressource de test",
        "curriculum_levels": ["premiere"],
        "topics": ["derivatives"],
        "prerequisites": ["derivative-basics"],
        "skills": ["reasoning"],
        "tags": ["rappel"],
        "priority": 0,
    }
    if kind == "course":
        value.update(summary="Un rappel concis.", content="Un contenu pédagogique autonome et français.")
    elif kind == "example":
        value.update(statement="Étudier une autre fonction.", solution="On calcule puis on conclut.")
    elif kind == "video":
        value.update(provider="youtube", url="https://www.youtube.com/watch?v=fixture-resource-01",
                     author="Auteur de test", duration_minutes=8)
    value.update(overrides)
    return value


def make_repository(tmp_path: Path, *values) -> ResourceRepository:
    tmp_path.mkdir(parents=True, exist_ok=True)
    for index, value in enumerate(values):
        (tmp_path / f"{index}.yaml").write_text(yaml.safe_dump(value, allow_unicode=True), encoding="utf-8")
    repository = ResourceRepository(tmp_path)
    repository.load()
    return repository


def test_missing_and_empty_resource_corpus_fail_fast(tmp_path):
    with pytest.raises(ResourceCorpusError, match="directory does not exist"):
        ResourceRepository(tmp_path / "missing").load()
    with pytest.raises(ResourceCorpusError, match="no YAML files found under"):
        ResourceRepository(tmp_path).load()


def test_version_controlled_resource_corpus_is_not_empty():
    repository = ResourceRepository(Path(__file__).resolve().parents[2] / "resources")
    repository.load()
    assert repository.count > 0


def context(**overrides):
    values = dict(curriculum_level=CurriculumLevel.PREMIERE, topics=(Topic.DERIVATIVES,),
                  prerequisites=("derivative-basics",), skills=(Skill.REASONING,))
    values.update(overrides)
    return ResourceContext(**values)


def test_repository_loads_all_canonical_types(tmp_path):
    repository = make_repository(tmp_path, resource(), resource("example", "example-item"),
                                 resource("video", "video-item"))
    assert repository.count == 3
    assert repository.get("example-item").type == "example"
    assert len(repository.list_by_type("video")) == 1


@pytest.mark.parametrize("change", [
    {"type": "podcast"}, {"id": "Bad slug"}, {"title": ""},
    {"topics": ["unknown-topic"]}, {"curriculum_levels": ["college"]},
    {"type": "video", "provider": "youtube", "url": "https://example.test/video",
     "author": "Auteur", "duration_minutes": 2},
])
def test_repository_rejects_invalid_resources(tmp_path, change):
    value = resource()
    value.update(change)
    with pytest.raises(ResourceCorpusError) as error:
        make_repository(tmp_path, value)
    assert "file:" in str(error.value)


def test_repository_rejects_duplicate_ids(tmp_path):
    with pytest.raises(ResourceCorpusError, match="duplicate ID"):
        make_repository(tmp_path, resource(), resource(identifier="course-item", title="Autre titre"))


def test_repository_rejects_duplicate_curriculum_refs(tmp_path):
    with pytest.raises(ResourceCorpusError, match="must not contain duplicates"):
        make_repository(tmp_path, resource(knowledge_ids=["derivatives", "derivatives"]))


def test_curriculum_refs_are_authoritative_and_level_compatible(tmp_path):
    curriculum = CurriculumRepository(Path(__file__).resolve().parents[2] / "curriculum")
    curriculum.load()
    for field, value, message in (
        ("knowledge_ids", ["invented-node"], "unknown knowledge ID"),
        ("curriculum_expectations", ["invented-expectation"], "unknown curriculum expectation"),
        ("curriculum_expectations", ["c4-2020-3e-equations"], "incompatible with curriculum_levels"),
    ):
        repository = make_repository(tmp_path / field, resource(**{field: value}))
        with pytest.raises(ResourceCorpusError, match=message):
            validate_resource_curriculum_refs(repository, curriculum)


def test_resolver_weighting_filtering_diversity_and_determinism(tmp_path):
    repository = make_repository(
        tmp_path,
        resource(identifier="prerequisite-match", topics=[], priority=0),
        resource("example", "topic-only", prerequisites=[], skills=[], priority=0),
        resource("example", "explicit-example", topics=[], prerequisites=[], skills=[]),
        resource("video", "skill-video", topics=[], prerequisites=[], skills=["reasoning"]),
        resource(identifier="wrong-level", curriculum_levels=["terminale"]),
        resource(identifier="irrelevant", topics=[], prerequisites=[], skills=[]),
    )
    resolver = ResourceResolver(repository)
    ctx = context(explicit_resource_refs=("explicit-example",))
    first = resolver.resolve(ctx)
    second = resolver.resolve(ctx)
    assert [item.resource.id for item in first] == ["explicit-example", "prerequisite-match", "skill-video"]
    assert [item.resource.id for item in second] == [item.resource.id for item in first]
    assert first[0].reasons[0] == "explicit:explicit-example"
    assert first[1].score > next(item.score for item in resolver.resolve(context()) if item.resource.id == "topic-only")
    assert "wrong-level" not in {item.resource.id for item in first}
    assert "irrelevant" not in {item.resource.id for item in first}
    assert len(first) == 3 and len({item.resource.type for item in first}) == 3
    assert len(resolver.resolve(ctx, limit=2)) == 2


def test_expectation_then_knowledge_precedence_and_level_safety(tmp_path):
    repository = make_repository(
        tmp_path,
        resource(identifier="generic-topic"),
        resource(identifier="knowledge-course", topics=[], prerequisites=[], skills=[],
                 knowledge_ids=["first-degree-equation"]),
        resource(identifier="expectation-course", topics=[], prerequisites=[], skills=[],
                 curriculum_expectations=["lycee-2019-1re-analysis"]),
        resource(identifier="explicit-course", topics=[], prerequisites=[], skills=[]),
        resource(identifier="unsafe-course", curriculum_levels=["terminale"], topics=[],
                 prerequisites=[], skills=[], knowledge_ids=["first-degree-equation"]),
    )
    result = ResourceResolver(repository).resolve(context(
        curriculum_expectations=("lycee-2019-1re-analysis",),
        knowledge_ids=("first-degree-equation",), explicit_resource_refs=("explicit-course",),
    ), limit=10)
    assert EXPLICIT_REF_WEIGHT > EXPECTATION_WEIGHT > KNOWLEDGE_WEIGHT
    assert [item.resource.id for item in result] == ["explicit-course"]  # strongest course per type
    all_courses = [ResourceResolver(make_repository(tmp_path / str(i), value)).resolve(context(
        curriculum_expectations=("lycee-2019-1re-analysis",), knowledge_ids=("first-degree-equation",)
    )) for i, value in enumerate((resource(identifier="generic-topic"),
        resource(identifier="knowledge-course", topics=[], prerequisites=[], skills=[], knowledge_ids=["first-degree-equation"]),
        resource(identifier="expectation-course", topics=[], prerequisites=[], skills=[], curriculum_expectations=["lycee-2019-1re-analysis"]))) ]
    assert all_courses[2][0].score > all_courses[1][0].score > all_courses[0][0].score
    assert "unsafe-course" not in {item.resource.id for item in result}


def test_generated_variants_share_curriculum_knowledge_resource():
    root = Path(__file__).resolve().parents[2]
    curriculum = CurriculumRepository(root / "curriculum"); curriculum.load()
    problems = ProblemRepository(root / "problems", curriculum); problems.load()
    resources = ResourceRepository(root / "resources"); resources.load()
    resolver = ResourceResolver(resources)
    variants = [p for p in problems.list() if p.id.startswith("3e-equation-")][:3]
    assert len(variants) == 3
    matches = [resolver.resolve(context_for_problem(problem, curriculum)) for problem in variants]
    assert all(not problem.resource_refs for problem in variants)
    assert all(next(x.resource.id for x in match if x.resource.type == "course") == "equation-isolation-basics"
               for match in matches)


@pytest.mark.parametrize("expectation_id", [
    "c4-2020-4e-fractions", "c4-2020-4e-pythagoras", "c4-2020-4e-statistics",
    "c4-2020-3e-powers", "c4-2020-3e-thales", "c4-2020-3e-functions",
])
def test_representative_college_expectations_resolve_a_course(expectation_id):
    root = Path(__file__).resolve().parents[2]
    curriculum = CurriculumRepository(root / "curriculum"); curriculum.load()
    problems = ProblemRepository(root / "problems", curriculum); problems.load()
    resources = ResourceRepository(root / "resources"); resources.load()
    problem = next(p for p in problems.list() if expectation_id in p.curriculum.expectations)
    matches = ResourceResolver(resources).resolve(context_for_problem(problem, curriculum))
    assert any(match.resource.type == "course" for match in matches)


def test_tutor_course_gap_uses_problem_curriculum_knowledge():
    root = Path(__file__).resolve().parents[2]
    curriculum = CurriculumRepository(root / "curriculum"); curriculum.load()
    problems = ProblemRepository(root / "problems", curriculum); problems.load()
    resources = ResourceRepository(root / "resources"); resources.load()
    problem = next(p for p in problems.list() if p.id.startswith("3e-equation-direct-") and not p.resource_refs)
    signal = SimpleNamespace(needed=True, need=ResourceNeed.COURSE_GAP, topics=(), prerequisites=(), skills=(), tags=())
    safe = SimpleNamespace(reveals_answer=False, confidence=1.0, intervention_needed=True)
    selected = select_resource(problem, signal, safe, 2, TutorTrigger.I_AM_STUCK,
                               ResourceResolver(resources), curriculum)
    assert selected.resource.id == "equation-isolation-basics"


def test_cross_corpus_validation_rejects_dangling_reference(tmp_path):
    problem_dir, resource_dir = tmp_path / "problems", tmp_path / "resources"
    problem_dir.mkdir(); resource_dir.mkdir()
    problem = {
        "id": "test-problem", "title": "Exercice", "statement": "Démontrer le résultat.",
        "curriculum": {"level": "premiere", "difficulty": 2}, "topics": ["derivatives"],
        "source": {"type": "internal", "name": "Test"}, "reference_solution": "Une preuve.",
        "resource_refs": ["missing-resource"],
    }
    (problem_dir / "problem.yaml").write_text(yaml.safe_dump(problem, allow_unicode=True), encoding="utf-8")
    problems = ProblemRepository(problem_dir); problems.load()
    resources = make_repository(resource_dir, resource())
    with pytest.raises(ResourceCorpusError, match="test-problem references unknown resource missing-resource"):
        validate_problem_resource_refs(problems, resources)
