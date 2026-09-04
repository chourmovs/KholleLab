from pydantic import BaseModel, ConfigDict

from app.domain.problem import Level, ProblemResources, SourceInfo, Topic


class PublicModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProblemCatalogueItem(PublicModel):
    id: str
    title: str
    subtitle: str | None
    level: Level
    difficulty: int
    estimated_minutes: int | None
    year: int | None
    topics: tuple[Topic, ...]
    source: SourceInfo


class ProblemPublicDetail(ProblemCatalogueItem):
    statement: str
    hint_levels: tuple[int, ...]
    resources: ProblemResources | None = None
