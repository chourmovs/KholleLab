from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Level(StrEnum):
    PREMIERE = "premiere"
    TERMINALE = "terminale"
    OLYMPIADES = "olympiades"
    CONCOURS_GENERAL = "concours-general"


class Topic(StrEnum):
    ALGEBRA = "algebra"
    ANALYSIS = "analysis"
    ARITHMETIC = "arithmetic"
    COMBINATORICS = "combinatorics"
    GEOMETRY = "geometry"
    INEQUALITIES = "inequalities"
    PROBABILITY = "probability"
    SEQUENCES = "sequences"
    FUNCTIONS = "functions"
    COMPLEX_NUMBERS = "complex-numbers"
    LOGIC = "logic"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceInfo(StrictModel):
    type: NonEmpty
    name: NonEmpty
    year: int | None = None
    session: NonEmpty | None = None
    url: str | None = None


class Hint(StrictModel):
    level: int = Field(ge=1, le=5)
    text: NonEmpty


class Problem(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    title: NonEmpty
    statement: NonEmpty
    level: Level
    difficulty: int = Field(ge=1, le=5)
    topics: tuple[Topic, ...] = Field(min_length=1)
    source: SourceInfo
    reference_solution: NonEmpty
    subtitle: NonEmpty | None = None
    estimated_minutes: int | None = Field(default=None, gt=0)
    year: int | None = None
    hints: tuple[Hint, ...] = ()
    authors: tuple[NonEmpty, ...] = ()
    tags: tuple[NonEmpty, ...] = ()
    notes: NonEmpty | None = None

    @model_validator(mode="after")
    def unique_hint_levels(self) -> "Problem":
        levels = [hint.level for hint in self.hints]
        if len(levels) != len(set(levels)):
            raise ValueError("hint levels must be unique")
        return self
