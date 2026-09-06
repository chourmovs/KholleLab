from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.db.base import Base
from app.models.attempt import Attempt, AttemptStatus
from app.models.evaluation import EvaluationStage, EvaluationStatus
from app.providers.llm import FakeLLMProvider, RemoteLLMError
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.services.examiner import ExaminerService, RetryNotAllowed
from app.services.problem_repository import ProblemRepository

@pytest.fixture
def setup():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine); Session=sessionmaker(bind=engine,expire_on_commit=False); db=Session()
    problems=ProblemRepository(str(Path(__file__).resolve().parents[2]/"problems"));problems.load();problem=problems.list()[0]
    attempt=Attempt(problem_id=problem.id,status=AttemptStatus.SUBMITTED,solution_markdown="Une preuve concise.");db.add(attempt);db.commit();db.refresh(attempt)
    repo=EvaluationRepository(db);service=ExaminerService(AttemptRepository(db),repo,problems,FakeLLMProvider())
    yield db,repo,service,attempt
    db.close()

def test_enqueue_is_idempotent_and_claims_once(setup):
    _,repo,service,attempt=setup
    first=service.enqueue(attempt.id);second=service.enqueue(attempt.id)
    assert first.id==second.id and first.stage==EvaluationStage.QUEUED
    claimed=repo.claim_next();assert claimed.id==first.id and claimed.stage==EvaluationStage.CANDIDATE_AUDIT
    assert repo.claim_next() is None

@pytest.mark.asyncio
async def test_worker_completes_both_passes(setup):
    _,repo,service,attempt=setup
    value=repo.claim_next() if service.enqueue(attempt.id) else None
    result=await service.process(value)
    assert result.status==EvaluationStatus.COMPLETED
    assert result.stage==EvaluationStage.COMPLETED and result.progress==100
    assert result.audit_json and result.result_json and result.elapsed_ms is not None

@pytest.mark.asyncio
async def test_worker_normalizes_controlled_failure_and_retry(setup):
    _,repo,service,attempt=setup
    class Broken(FakeLLMProvider):
        async def structured_response(self,**kwargs): raise RemoteLLMError("REMOTE_TIMEOUT","timeout")
    service.provider=Broken(); value=repo.claim_next() if service.enqueue(attempt.id) else None
    result=await service.process(value);assert result.status==EvaluationStatus.FAILED and result.error_code=="REMOTE_TIMEOUT"
    restarted=service.enqueue(attempt.id,retry=True);assert restarted.stage==EvaluationStage.QUEUED
    with pytest.raises(RetryNotAllowed): service.enqueue(attempt.id,retry=True)

@pytest.mark.asyncio
async def test_transient_failure_is_durably_delayed_and_due_claimed(setup,monkeypatch):
    _,repo,service,attempt=setup
    class Unavailable(FakeLLMProvider):
        async def structured_response(self,**kwargs): raise RemoteLLMError("REMOTE_PROVIDER","unavailable",status=503,retryable=True)
    service.provider=Unavailable(); value=repo.claim_next() if service.enqueue(attempt.id) else None
    result=await service.process(value)
    assert result.status==EvaluationStatus.RUNNING and result.stage==EvaluationStage.QUEUED
    assert result.provider_retry_count==1 and result.next_retry_at and result.completed_at is None
    assert repo.claim_next() is None
    result.next_retry_at=datetime.now(timezone.utc)-timedelta(seconds=1);repo.db.commit()
    assert repo.claim_next().id==result.id

@pytest.mark.asyncio
async def test_adjudication_retry_preserves_and_resumes_audit(setup,monkeypatch):
    _,repo,service,attempt=setup
    successful=FakeLLMProvider()
    class AuditThenUnavailable(FakeLLMProvider):
        def __init__(self): self.calls=[]
        async def structured_response(self,**kwargs):
            self.calls.append(kwargs["response_model"])
            if len(self.calls)==1: return await successful.structured_response(**kwargs)
            raise RemoteLLMError("REMOTE_PROVIDER","unavailable",status=503,retryable=True)
    unavailable=AuditThenUnavailable(); service.provider=unavailable
    value=repo.claim_next() if service.enqueue(attempt.id) else None
    delayed=await service.process(value)
    assert delayed.audit_json and delayed.stage==EvaluationStage.QUEUED
    delayed.next_retry_at=datetime.now(timezone.utc)-timedelta(seconds=1);repo.db.commit()
    resumed=repo.claim_next(); service.provider=successful
    completed=await service.process(resumed)
    assert completed.status==EvaluationStatus.COMPLETED
    assert len(unavailable.calls)==2

@pytest.mark.asyncio
async def test_transient_retry_exhaustion_fails_and_manual_retry_resets(setup,monkeypatch):
    _,repo,service,attempt=setup
    monkeypatch.setattr(__import__("app.core.config",fromlist=["settings"]).settings,"evaluation_provider_max_retries",0)
    class Unavailable(FakeLLMProvider):
        async def structured_response(self,**kwargs): raise RemoteLLMError("REMOTE_PROVIDER","unavailable",status=503,retryable=True)
    service.provider=Unavailable(); value=repo.claim_next() if service.enqueue(attempt.id) else None
    failed=await service.process(value)
    assert failed.status==EvaluationStatus.FAILED
    failed.provider_retry_count=3;failed.next_retry_at=datetime.now(timezone.utc);repo.db.commit()
    restarted=service.enqueue(attempt.id,retry=True)
    assert restarted.provider_retry_count==0 and restarted.next_retry_at is None and restarted.audit_json is None

def test_stale_worker_requeues_once_then_fails(setup):
    _,repo,service,attempt=setup
    value=repo.claim_next() if service.enqueue(attempt.id) else None
    value.heartbeat_at=datetime.now(timezone.utc)-timedelta(minutes=10);repo.db.commit()
    assert repo.recover_stale(60)==1;assert value.stage==EvaluationStage.QUEUED and value.recovery_count==1
    value=repo.claim_next();value.heartbeat_at=datetime.now(timezone.utc)-timedelta(minutes=10);repo.db.commit()
    assert repo.recover_stale(60)==1;assert value.status==EvaluationStatus.FAILED and value.error_code=="worker_interrupted"

def test_restart_resets_recovery_and_null_heartbeat_is_recovered(setup):
    _,repo,service,attempt=setup
    value=repo.claim_next() if service.enqueue(attempt.id) else None
    value.recovery_count=1;value.heartbeat_at=None;repo.db.commit()
    assert repo.recover_stale(60)==1
    assert value.status==EvaluationStatus.FAILED
    restarted=service.enqueue(attempt.id,retry=True)
    assert restarted.recovery_count==0
