from datetime import datetime
from pydantic import BaseModel

from app.domain.problem import CurriculumLevel


class CurriculumLevelMetrics(BaseModel):
    level: CurriculumLevel
    eligible: int
    solved: int
    progress: float
    progress_percent: float


class CurriculumLevelProgress(CurriculumLevelMetrics):
    unlocked: bool
    current: bool


class CurriculumProgressSummary(BaseModel):
    initial_level: CurriculumLevel
    current_level: CurriculumLevel
    highest_unlocked_level: CurriculumLevel
    onboarding_completed: bool
    unlock_ratio: float
    current: CurriculumLevelMetrics
    next_level: CurriculumLevel | None
    next_level_unlocked: bool
    can_advance: bool
    remaining_to_unlock: int
    levels: list[CurriculumLevelProgress]


class CurriculumLevelChoice(BaseModel):
    level: CurriculumLevel


class CurriculumProgressHistoryPoint(BaseModel):
    at: datetime
    solved: int
    progress_percent: float


class CurriculumProgressHistory(BaseModel):
    level: CurriculumLevel
    eligible: int
    unlock_required: int
    points: list[CurriculumProgressHistoryPoint]
