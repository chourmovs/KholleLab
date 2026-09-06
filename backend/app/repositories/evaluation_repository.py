import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation, EvaluationStage, EvaluationStatus
from app.schemas.evaluation import CandidateAudit, EvaluationResult

NOW = lambda: datetime.now(timezone.utc)

class EvaluationRepository:
    def __init__(self, db: Session): self.db = db

    def get_for_attempt(self, attempt_id: uuid.UUID):
        return self.db.query(Evaluation).filter_by(attempt_id=attempt_id).one_or_none()

    def enqueue(self, attempt_id, provider, model, prompt_version="examiner-v1"):
        existing = self.get_for_attempt(attempt_id)
        if existing: return existing
        value = Evaluation(attempt_id=attempt_id, status=EvaluationStatus.RUNNING,
                           stage=EvaluationStage.QUEUED, progress=5, provider=provider,
                           model=model, prompt_version=prompt_version)
        self.db.add(value)
        try: self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return self.get_for_attempt(attempt_id)
        self.db.refresh(value)
        return value

    def claim_next(self):
        statement = (select(Evaluation).where(
            Evaluation.status == EvaluationStatus.RUNNING,
            Evaluation.stage == EvaluationStage.QUEUED,
        ).order_by(Evaluation.created_at).with_for_update(skip_locked=True).limit(1))
        value = self.db.execute(statement).scalar_one_or_none()
        if value:
            now = NOW(); value.stage = EvaluationStage.CANDIDATE_AUDIT; value.progress = 25
            value.started_at = value.started_at or now; value.heartbeat_at = now
            self.db.commit(); self.db.refresh(value)
        return value

    def set_stage(self, value, stage: EvaluationStage, progress: int):
        value.stage, value.progress, value.heartbeat_at = stage, progress, NOW()
        self.db.commit(); self.db.refresh(value); return value

    def heartbeat(self, value):
        """Renew ownership of a running evaluation during slow provider calls."""
        value.heartbeat_at = NOW()
        self.db.commit()

    def store_audit(self, value, audit: CandidateAudit):
        value.audit_json = audit.model_dump(mode="json")
        return self.set_stage(value, EvaluationStage.ADJUDICATION, 60)

    def complete(self, value, audit: CandidateAudit, result: EvaluationResult, elapsed_ms=None):
        value.status=EvaluationStatus.COMPLETED; value.stage=EvaluationStage.COMPLETED; value.progress=100
        value.audit_json=audit.model_dump(mode="json"); value.result_json=result.model_dump(mode="json")
        value.score=result.score; value.verdict=result.verdict; value.confidence=result.confidence
        value.completed_at=NOW(); value.heartbeat_at=NOW(); value.elapsed_ms=elapsed_ms; value.error_code=None
        self.db.commit(); self.db.refresh(value); return value

    def fail(self, value, code="REMOTE_PROVIDER"):
        value.status=EvaluationStatus.FAILED; value.stage=EvaluationStage.FAILED; value.progress=100
        value.error_code=code; value.completed_at=NOW(); value.heartbeat_at=NOW()
        self.db.commit(); self.db.refresh(value); return value

    def restart(self, value):
        value.status=EvaluationStatus.RUNNING; value.stage=EvaluationStage.QUEUED; value.progress=5
        value.error_code=None; value.completed_at=None; value.started_at=None; value.heartbeat_at=None
        value.audit_json=None; value.result_json=None; value.elapsed_ms=None
        value.recovery_count=0
        self.db.commit(); self.db.refresh(value); return value

    def recover_stale(self, stale_seconds: int):
        cutoff = NOW() - timedelta(seconds=stale_seconds)
        values = self.db.query(Evaluation).filter(
            Evaluation.status == EvaluationStatus.RUNNING,
            Evaluation.stage != EvaluationStage.QUEUED,
            (Evaluation.heartbeat_at.is_(None)) | (Evaluation.heartbeat_at < cutoff),
        ).with_for_update(skip_locked=True).all()
        for value in values:
            if value.recovery_count < 1:
                value.recovery_count += 1; value.stage=EvaluationStage.QUEUED; value.progress=5
                value.started_at=None; value.heartbeat_at=None; value.audit_json=None
            else:
                value.status=EvaluationStatus.FAILED; value.stage=EvaluationStage.FAILED
                value.progress=100; value.error_code="worker_interrupted"; value.completed_at=NOW()
        self.db.commit()
        return len(values)
