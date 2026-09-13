from pydantic import BaseModel

from app.domain.problem import CurriculumLevel


class CurriculumLevelProgress(BaseModel):
    level: CurriculumLevel
    eligible: int
    solved: int
    progress: float
    progress_percent: float
    unlocked: bool
    current: bool


class CurriculumProgressSummary(BaseModel):
    initial_level: CurriculumLevel
    current_level: CurriculumLevel
    highest_unlocked_level: CurriculumLevel
    onboarding_completed: bool
    unlock_ratio: float
    levels: list[CurriculumLevelProgress]


class CurriculumLevelChoice(BaseModel):
    level: CurriculumLevel
