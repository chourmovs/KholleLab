from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MasteryState(StrEnum):
    NOT_ENOUGH_DATA = "not_enough_data"
    EMERGING = "emerging"
    PRACTICING = "practicing"
    ESTABLISHED = "established"


class ProfileActivitySummary(BaseModel):
    sessions_total: int
    sessions_completed: int
    sessions_abandoned: int
    attempts_total: int
    evaluations_completed: int
    sessions_last_7_days: int
    sessions_last_30_days: int
    completed_last_30_days: int


class MasteryEvidenceSummary(BaseModel):
    identifier: str
    label: str
    state: MasteryState
    evidence_count: int
    completed_sessions: int
    abandoned_sessions: int
    recent_sessions: int
    difficulty_min: int
    difficulty_max: int
    highest_positive_difficulty: int | None
    last_practiced_at: datetime
    support_signals: list[str]


class KnowledgeMasterySummary(BaseModel):
    identifier: str
    label: str
    kind: str
    parent: str | None
    parent_label: str | None = None
    state: MasteryState
    evidence_count: int = Field(description="All observations for this node in the bounded profile window.")
    assessed_evidence_count: int = Field(description="Assessed observations in the current mastery window.")
    positive_count: int = Field(description="Positive observations in the current assessed mastery window.")
    partial_count: int = Field(description="Partial observations in the current assessed mastery window.")
    negative_count: int = Field(description="Negative observations in the current assessed mastery window.")
    incomplete_sessions: int = Field(description="Incomplete observations in the recent activity window.")
    unassessed_sessions: int = Field(description="Unassessed observations in the recent activity window.")
    difficulty_min: int
    difficulty_max: int
    highest_positive_difficulty: int | None
    last_practiced_at: datetime
    support_signals: list[str]


class ConsolidationItem(BaseModel):
    kind: str
    identifier: str
    label: str
    state: MasteryState
    reasons: list[str]
    prerequisites: list[dict[str, str]] = Field(default_factory=list)


class EvidenceWindow(BaseModel):
    sessions_considered: int
    max_sessions: int


class LearnerProfileResponse(BaseModel):
    # Deprecated compatibility projections. KnowledgeNode summaries are canonical.
    activity: ProfileActivitySummary
    topics: list[MasteryEvidenceSummary]
    skills: list[MasteryEvidenceSummary]
    knowledge: list[KnowledgeMasterySummary]
    strengths: list[KnowledgeMasterySummary]
    needs_consolidation: list[ConsolidationItem]
    generated_at: datetime
    evidence_window: EvidenceWindow
