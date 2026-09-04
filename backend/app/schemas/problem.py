from pydantic import BaseModel, ConfigDict

from app.domain.problem import CurriculumInfo, CurriculumLevel, ProblemResources, SourceInfo, Topic, Skill


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


class ProblemSelectionResult(PublicModel):
    problem: ProblemPublicDetail | None
    requested_level: CurriculumLevel
    requested_difficulty: int | None
    actual_difficulty: int | None
    fallback_used: bool
