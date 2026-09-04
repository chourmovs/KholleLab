import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.evaluation import Evaluation, EvaluationStatus
from app.schemas.evaluation import CandidateAudit, EvaluationResult

class EvaluationRepository:
    def __init__(self, db: Session): self.db=db
    def get_for_attempt(self, attempt_id: uuid.UUID):
        return self.db.query(Evaluation).filter_by(attempt_id=attempt_id).one_or_none()
    def create_running(self, attempt_id, provider, model, prompt_version="examiner-v1"):
        value=Evaluation(attempt_id=attempt_id,status=EvaluationStatus.RUNNING,provider=provider,model=model,prompt_version=prompt_version)
        self.db.add(value); self.db.commit(); self.db.refresh(value); return value
    def complete(self, value, audit: CandidateAudit, result: EvaluationResult):
        value.status=EvaluationStatus.COMPLETED; value.audit_json=audit.model_dump(mode="json"); value.result_json=result.model_dump(mode="json"); value.score=result.score; value.verdict=result.verdict; value.confidence=result.confidence; value.completed_at=datetime.now(timezone.utc); value.error_code=None
        self.db.commit(); self.db.refresh(value); return value
    def fail(self, value, code="provider_error"):
        value.status=EvaluationStatus.FAILED; value.error_code=code; value.completed_at=datetime.now(timezone.utc); self.db.commit(); self.db.refresh(value); return value
    def restart(self, value):
        value.status=EvaluationStatus.RUNNING; value.error_code=None; value.completed_at=None; value.started_at=datetime.now(timezone.utc); self.db.commit(); return value
