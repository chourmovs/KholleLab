import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.attempt import utcnow


class GeneratedProblemStatus(str, enum.Enum):
    ACCEPTED = "accepted"
    RETIRED = "retired"


class GeneratedProblem(Base):
    """A global catalogue record. Deliberately contains no learner identity."""

    __tablename__ = "generated_problems"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_generated_problems_content_hash"),
        Index("ix_generated_problems_bucket", "programme_id", "level", "expectation_id", "difficulty", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[GeneratedProblemStatus] = mapped_column(
        Enum(GeneratedProblemStatus, name="generated_problem_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False, default=GeneratedProblemStatus.ACCEPTED,
    )
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    programme_id: Mapped[str] = mapped_column(String(128), nullable=False)
    expectation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    generator_family: Mapped[str] = mapped_column(String(64), nullable=False)
    generator_model: Mapped[str] = mapped_column(String(255), nullable=False)
    generator_prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    critic_family: Mapped[str] = mapped_column(String(64), nullable=False)
    critic_model: Mapped[str] = mapped_column(String(255), nullable=False)
    critic_prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
