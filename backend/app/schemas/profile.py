from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


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


class ConsolidationItem(BaseModel):
    kind: str
    identifier: str
    label: str
    state: MasteryState
    reasons: list[str]


class EvidenceWindow(BaseModel):
    sessions_considered: int
    max_sessions: int


class LearnerProfileResponse(BaseModel):
    activity: ProfileActivitySummary
    topics: list[MasteryEvidenceSummary]
    skills: list[MasteryEvidenceSummary]
    strengths: list[MasteryEvidenceSummary]
    needs_consolidation: list[ConsolidationItem]
    generated_at: datetime
    evidence_window: EvidenceWindow
