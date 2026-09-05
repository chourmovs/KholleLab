from pathlib import Path

import pytest
import yaml

from app.domain.problem import CurriculumLevel, Skill, Topic
from app.services.problem_repository import ProblemRepository
from app.services.resource_repository import (
    ResourceCorpusError,
    ResourceRepository,
    validate_problem_resource_refs,
)
from app.services.resource_resolver import ResourceContext, ResourceResolver


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
    for index, value in enumerate(values):
        (tmp_path / f"{index}.yaml").write_text(yaml.safe_dump(value, allow_unicode=True), encoding="utf-8")
    repository = ResourceRepository(tmp_path)
    repository.load()
    return repository


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
    resources = ResourceRepository(resource_dir); resources.load()
    with pytest.raises(ResourceCorpusError, match="test-problem references unknown resource missing-resource"):
        validate_problem_resource_refs(problems, resources)
