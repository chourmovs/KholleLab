from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.domain.problem import CurriculumInfo, CurriculumLevel, ProblemResources, SourceInfo, Topic, Skill


def to_public_problem_detail(problem) -> "ProblemPublicDetail":
    """Allow-list the fields exposed by every public problem payload."""
    return ProblemPublicDetail.model_validate({
        "id": problem.id,
        "title": problem.title,
        "subtitle": problem.subtitle,
        "statement": problem.statement,
        "curriculum": problem.curriculum,
        "estimated_minutes": problem.estimated_minutes,
        "year": problem.year,
        "topics": problem.topics,
        "source": problem.source,
        "hint_levels": tuple(hint.level for hint in problem.hints),
        "prerequisites": problem.prerequisites,
        "skills": problem.skills,
        "resources": problem.resources,
        "resource_refs": problem.resource_refs,
    })


class PublicModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProblemCatalogueItem(PublicModel):
    id: str
    title: str
    subtitle: str | None
    curriculum: CurriculumInfo
    estimated_minutes: int | None
    year: int | None
    topics: tuple[Topic, ...]
    source: SourceInfo


class ProblemPublicDetail(ProblemCatalogueItem):
    statement: str
    hint_levels: tuple[int, ...]
    prerequisites: tuple[str, ...]
    skills: tuple[Skill, ...]
    resources: ProblemResources | None = None
    resource_refs: tuple[str, ...] = ()


class SelectionMode(StrEnum):
    MANUAL = "manual"
    ADAPTIVE = "adaptive"
    FALLBACK = "fallback"


class ProblemSelectionAdaptation(PublicModel):
    reason_codes: tuple[str, ...] = ()
    targeted_topics: tuple[Topic, ...] = ()
    targeted_skills: tuple[Skill, ...] = ()
    targeted_prerequisites: tuple[str, ...] = ()


class ProblemSelectionResult(PublicModel):
    problem: ProblemPublicDetail | None
    requested_level: CurriculumLevel
    requested_difficulty: int | None
    actual_difficulty: int | None
    fallback_used: bool
    selection_mode: SelectionMode = SelectionMode.MANUAL
    adaptation: ProblemSelectionAdaptation | None = None
