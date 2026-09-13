from datetime import date

from pydantic import BaseModel


class ProgressionSummary(BaseModel):
    total_xp: int
    grade: int
    current_grade_start_xp: int
    next_grade_xp: int
    xp_to_next_grade: int
    current_streak_days: int
    longest_streak_days: int
    active_today: bool
    last_active_date: date | None
    completed_sessions: int
    timezone: str
