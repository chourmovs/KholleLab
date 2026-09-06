import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.learning_session import LearningSessionStatus
from app.schemas.attempt import AttemptResponse
from app.schemas.tutor import TutorResponse


class SessionStart(BaseModel):
    problem_id: str = Field(min_length=1, max_length=255)
    force_new: bool = False


class SessionSummary(BaseModel):
    session_id: uuid.UUID
    problem_id: str
    problem_title: str
    status: LearningSessionStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int
    number_of_attempts: int
    number_of_tutor_interactions: int
    outcome: str | None = None


class SessionDetail(SessionSummary):
    problem: dict | None
    attempts: list[AttemptResponse]
    current_attempt_id: uuid.UUID | None
    final_work: str
    tutor_assessment: TutorResponse | None
    resource_recommendation: dict | None


class SessionTransition(BaseModel):
    expected_status: LearningSessionStatus = LearningSessionStatus.ACTIVE
