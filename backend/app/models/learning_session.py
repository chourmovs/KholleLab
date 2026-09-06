import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.attempt import utcnow


class LearningSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        Index("ix_learning_sessions_updated_at", "updated_at"),
        Index("ix_learning_sessions_problem_id", "problem_id"),
        Index("ix_learning_sessions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # A nullable unique key gives each problem at most one active session while
    # allowing any number of immutable completed/abandoned sessions.
    active_problem_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[LearningSessionStatus] = mapped_column(
        Enum(LearningSessionStatus, name="learning_session_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=LearningSessionStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_attempt_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
