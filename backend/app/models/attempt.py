import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AttemptStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint("elapsed_seconds >= 0", name="ck_attempt_elapsed_nonnegative"),
        CheckConstraint("revision >= 0", name="ck_attempt_revision_nonnegative"),
        Index("ix_attempts_problem_id", "problem_id"),
        Index("ix_attempts_updated_at", "updated_at"),
        Index("ix_attempts_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(Enum(AttemptStatus, name="attempt_status", values_callable=lambda e: [x.value for x in e]), nullable=False, default=AttemptStatus.DRAFT)
    solution_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    elapsed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
