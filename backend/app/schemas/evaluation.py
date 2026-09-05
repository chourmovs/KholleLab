from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Verdict = Literal["correct", "mostly_correct", "partial", "incorrect", "non_answer"]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class MathIssue(StrictModel):
    severity: Literal["minor", "major"]
    category: Literal["logic", "calculation", "algebra", "definition", "theorem", "domain", "rigor", "conclusion", "other"]
    description: str
    candidate_excerpt: str | None = None

class ClaimAssessment(StrictModel):
    statement: str
    status: Literal["valid", "invalid", "unjustified", "unclear"]
    explanation: str

class CandidateAudit(StrictModel):
    strategy_summary: str
    claims: list[ClaimAssessment]
    major_errors: list[MathIssue]
    minor_errors: list[MathIssue]
    missing_justifications: list[str]
    conclusion_reached: bool
    conclusion_supported: bool
    provisional_status: Verdict

class EvaluationRubric(StrictModel):
    mathematical_correctness: float = Field(ge=0, le=10)
    rigor: float = Field(ge=0, le=5)
    clarity: float = Field(ge=0, le=2)
    efficiency: float = Field(ge=0, le=3)

class EvaluationResult(StrictModel):
    verdict: Verdict
    score: float = Field(ge=0, le=20)
    max_score: Literal[20] = 20
    confidence: float = Field(ge=0, le=1)
    strategy_summary: str
    reference_relationship: Literal["same_strategy", "similar_strategy", "alternative_valid_strategy", "alternative_invalid_strategy", "no_meaningful_strategy"]
    rubric: EvaluationRubric
    strengths: list[str]
    issues: list[MathIssue]
    missing_justifications: list[str]
    key_feedback: str
    reference_method_summary: str
    suggested_improvement: str

    @model_validator(mode="after")
    def rubric_matches_score(self):
        total = self.rubric.mathematical_correctness + self.rubric.rigor + self.rubric.clarity + self.rubric.efficiency
        if abs(total - self.score) > 0.11:
            raise ValueError("rubric total must match score")
        return self

class EvaluationResponse(BaseModel):
    provider: str | None = None
    model: str | None = None
    status: Literal["running", "completed", "failed"]
    verdict: str | None = None
    score: float | None = None
    max_score: int = 20
    confidence: float | None = None
    strategy_summary: str | None = None
    reference_relationship: str | None = None
    rubric: EvaluationRubric | None = None
    strengths: list[str] = []
    issues: list[MathIssue] = []
    missing_justifications: list[str] = []
    key_feedback: str | None = None
    reference_method_summary: str | None = None
    suggested_improvement: str | None = None
    error_code: str | None = None
