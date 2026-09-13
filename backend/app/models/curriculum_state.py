import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.attempt import utcnow


class LearnerCurriculumState(Base):
    __tablename__ = "learner_curriculum_states"

    learner_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    initial_level: Mapped[str] = mapped_column(String(32), nullable=False)
    current_level: Mapped[str] = mapped_column(String(32), nullable=False)
    highest_unlocked_level: Mapped[str] = mapped_column(String(32), nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
