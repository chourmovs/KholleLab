from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class CurriculumLevel(StrEnum):
    SECONDE = "seconde"
    PREMIERE = "premiere"
    TERMINALE = "terminale"
    MATHS_SUP = "maths-sup"
    MATHS_SPE = "maths-spe"


CURRICULUM_ORDER = [level.value for level in CurriculumLevel]


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
    EQUATIONS = "equations"
    TRIGONOMETRY = "trigonometry"
    DERIVATIVES = "derivatives"
    INTEGRALS = "integrals"
    LIMITS = "limits"
    LINEAR_ALGEBRA = "linear-algebra"
    POLYNOMIALS = "polynomials"
    DIFFERENTIAL_EQUATIONS = "differential-equations"


class Skill(StrEnum):
    CALCULATION = "calculation"
    PROOF = "proof"
    REASONING = "reasoning"
    MODELING = "modeling"
    SIGN_ANALYSIS = "sign-analysis"
    GRAPH_READING = "graph-reading"
    EQUATION_SOLVING = "equation-solving"
    INEQUALITY_SOLVING = "inequality-solving"
    INDUCTION = "induction"
    CONTRADICTION = "contradiction"
    CASE_ANALYSIS = "case-analysis"
    CONSTRUCTION = "construction"
    ESTIMATION = "estimation"
    OPTIMIZATION = "optimization"


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


class CoursePoint(StrictModel):
    title: NonEmpty
    summary: NonEmpty
    topics: tuple[NonEmpty, ...] = ()


class VideoResource(StrictModel):
    title: NonEmpty
    provider: Literal["youtube"]
    url: HttpUrl
    author: NonEmpty | None = None
    duration_minutes: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_youtube_url(self) -> "VideoResource":
        if self.url.host not in {"youtube.com", "www.youtube.com", "youtu.be"}:
            raise ValueError("youtube resources must use a YouTube URL")
        return self


class ProblemResources(StrictModel):
    course_points: tuple[CoursePoint, ...] = ()
    videos: tuple[VideoResource, ...] = ()


class CurriculumInfo(StrictModel):
    level: CurriculumLevel
    difficulty: int = Field(ge=1, le=5)


class Problem(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    title: NonEmpty
    statement: NonEmpty
    curriculum: CurriculumInfo
    topics: tuple[Topic, ...] = Field(min_length=1)
    prerequisites: tuple[Slug, ...] = ()
    skills: tuple[Skill, ...] = ()
    recommended_after: tuple[Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")], ...] = ()
    source: SourceInfo
    reference_solution: NonEmpty
    subtitle: NonEmpty | None = None
    estimated_minutes: int | None = Field(default=None, gt=0)
    year: int | None = None
    hints: tuple[Hint, ...] = ()
    authors: tuple[NonEmpty, ...] = ()
    tags: tuple[Slug, ...] = ()
    notes: NonEmpty | None = None
    resources: ProblemResources | None = None
    # Legacy inline resources remain readable while the shared catalogue is adopted.
    resource_refs: tuple[Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")], ...] = ()

    @model_validator(mode="after")
    def unique_hint_levels(self) -> "Problem":
        levels = [hint.level for hint in self.hints]
        if len(levels) != len(set(levels)):
            raise ValueError("hint levels must be unique")
        for name in ("topics", "skills", "prerequisites", "tags", "resource_refs", "recommended_after"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must not contain duplicates")
        return self
