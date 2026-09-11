from pydantic import BaseModel, ConfigDict, Field


class StrictGenerationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeneratedProblemDraft(StrictGenerationModel):
    title: str = Field(min_length=1, max_length=160)
    statement: str = Field(min_length=1, max_length=6000)
    reference_solution: str = Field(min_length=1, max_length=10000)
    hints: tuple[str, ...] = Field(default=(), max_length=5)
    estimated_minutes: int = Field(ge=1, le=120)
    archetype: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ProblemGenerationCriticResult(StrictGenerationModel):
    mathematical_correctness: bool
    reference_solution_correctness: bool
    well_posed: bool
    level_appropriate: bool
    curriculum_aligned: bool
    difficulty_plausible: bool
    unambiguous: bool
    no_answer_leakage: bool
    issue_codes: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return all((self.mathematical_correctness, self.reference_solution_correctness,
                    self.well_posed, self.level_appropriate, self.curriculum_aligned,
                    self.difficulty_plausible, self.unambiguous, self.no_answer_leakage))


class GeneratedProblemSelectRequest(StrictGenerationModel):
    level: str
    expectation: str
    difficulty: int = Field(ge=1, le=5)
    domain: str | None = None


class GeneratedProblemSelectResponse(StrictGenerationModel):
    problem: dict
    pool_reused: bool
