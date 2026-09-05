import enum, uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class EvaluationStatus(str, enum.Enum):
    RUNNING="running"; COMPLETED="completed"; FAILED="failed"

class EvaluationStage(str, enum.Enum):
    QUEUED="queued"; CANDIDATE_AUDIT="candidate_audit"; ADJUDICATION="adjudication"; FINALIZING="finalizing"; COMPLETED="completed"; FAILED="failed"

class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("attempts.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus, name="evaluation_status", values_callable=lambda e:[x.value for x in e]), nullable=False)
    stage: Mapped[EvaluationStage] = mapped_column(Enum(EvaluationStage, name="evaluation_stage", values_callable=lambda e:[x.value for x in e]), default=EvaluationStage.QUEUED, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float|None] = mapped_column(Float)
    verdict: Mapped[str|None] = mapped_column(String(32))
    confidence: Mapped[float|None] = mapped_column(Float)
    audit_json: Mapped[dict|None] = mapped_column(JSON)
    result_json: Mapped[dict|None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda:datetime.now(timezone.utc), nullable=False)
    started_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    recovery_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    elapsed_ms: Mapped[float|None] = mapped_column(Float)
    completed_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str|None] = mapped_column(String(64))
