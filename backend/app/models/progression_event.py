import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.attempt import utcnow


class ProgressionEventType(str, enum.Enum):
    SESSION_COMPLETED = "session_completed"


class ProgressionEvent(Base):
    """Immutable practice event whose ownership follows its learning session."""

    __tablename__ = "progression_events"
    __table_args__ = (
        UniqueConstraint("session_id", "event_type", name="uq_progression_events_session_type"),
        Index("ix_progression_events_session_id", "session_id"),
        Index("ix_progression_events_activity_date", "activity_date"),
        Index("ix_progression_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[ProgressionEventType] = mapped_column(
        Enum(ProgressionEventType, name="progression_event_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    xp: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
