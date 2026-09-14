from datetime import date
from typing import Literal

from pydantic import BaseModel


class PracticeMilestone(BaseModel):
    id: str
    label: str
    kind: Literal["sessions", "xp", "streak"]
    unlocked: bool
    current: int
    target: int


class ProgressionSummary(BaseModel):
    total_xp: int
    xp_rank: int
    current_rank_start_xp: int
    next_rank_xp: int
    xp_to_next_rank: int
    current_streak_days: int
    longest_streak_days: int
    active_today: bool
    last_active_date: date | None
    completed_sessions: int
    today_xp: int
    daily_goal_xp: int
    daily_goal_completed: bool
    milestones: list[PracticeMilestone]
    timezone: str
