import asyncio, contextlib, json, time, uuid
from datetime import timedelta
from pathlib import Path

from app.core.config import settings
from app.core.logging import component_logger
from app.models.attempt import AttemptStatus
from app.models.evaluation import EvaluationStage, EvaluationStatus
from app.providers.llm import ModelRole, RemoteLLMError
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.evaluation_repository import NOW, EvaluationRepository
from app.schemas.evaluation import CandidateAudit, EvaluationResult
from sqlalchemy.exc import SQLAlchemyError

log=component_logger("examiner"); PROMPT_VERSION="examiner-v1"
class AttemptNotSubmitted(Exception): pass
class EvaluationNotFound(Exception): pass
class RetryNotAllowed(Exception): pass
class ExaminerAttemptNotFound(Exception): pass
class ExaminerProblemNotFound(Exception): pass

class ExaminerService:
    def __init__(self, attempts, evaluations, problems, provider):
        self.attempts=attempts; self.evaluations=evaluations; self.problems=problems; self.provider=provider
    def _prompt(self,name): return (Path(__file__).parent.parent/"prompts"/name).read_text()
    def enqueue(self, attempt_id: uuid.UUID, retry=False):
        attempt=self.attempts.get(attempt_id)
        if not attempt: raise ExaminerAttemptNotFound
        if attempt.status != AttemptStatus.SUBMITTED: raise AttemptNotSubmitted
        if not self.problems.get(attempt.problem_id): raise ExaminerProblemNotFound
        value=self.evaluations.get_for_attempt(attempt_id)
        if value:
            if not retry: return value
            if value.status != EvaluationStatus.FAILED: raise RetryNotAllowed
            return self.evaluations.restart(value)
        if retry: raise EvaluationNotFound
        return self.evaluations.enqueue(attempt_id,self.provider.name,self.provider.model,PROMPT_VERSION)

    async def process(self, value):
        started=time.perf_counter(); attempt=self.attempts.get(value.attempt_id)
        problem=self.problems.get(attempt.problem_id) if attempt else None
        if not attempt or not problem: return self.evaluations.fail(value,"evaluation_input_missing")
        candidate=f"<problem>\n{problem.statement}\n</problem>\n<candidate_solution>\n{attempt.solution_markdown}\n</candidate_solution>"
        # End the read transaction before provider backoff sleeps. Provider calls
        # never hold a PostgreSQL transaction or row lock open.
        self.evaluations.db.commit()
        heartbeat = asyncio.create_task(self._heartbeat(value))
        try:
            if value.audit_json:
                audit=CandidateAudit.model_validate(value.audit_json)
                log.info("evaluation_pass_resumed evaluation={} pass=adjudication", value.id)
            else:
                log.info("evaluation_pass_started evaluation={} pass=candidate_audit", value.id)
                audit=await self.provider.structured_response(instructions=self._prompt("examiner_audit_v1.md"),input_text=candidate,response_model=CandidateAudit,role=ModelRole.DEEP)
                self.evaluations.store_audit(value,audit)
            compact=json.dumps(audit.model_dump(mode="json",exclude_none=True),ensure_ascii=False,separators=(",",":"))
            adjudication=candidate+f"\n<candidate_audit>\n{compact}\n</candidate_audit>\n<reference_solution>\n{problem.reference_solution}\n</reference_solution>"
            log.info("evaluation_pass_started evaluation={} pass=adjudication", value.id)
            result=await self.provider.structured_response(instructions=self._prompt("examiner_adjudication_v1.md"),input_text=adjudication,response_model=EvaluationResult,role=ModelRole.DEEP)
            self.evaluations.set_stage(value,EvaluationStage.FINALIZING,95)
            elapsed=round((time.perf_counter()-started)*1000,1)
            log.info("evaluation_completed evaluation={} total_elapsed_ms={}",value.id,elapsed)
            return self.evaluations.complete(value,audit,EvaluationResult.model_validate(result),elapsed)
        except RemoteLLMError as exc:
            self.evaluations.db.rollback()
            if exc.retryable and value.provider_retry_count < settings.evaluation_provider_max_retries:
                retry_count=value.provider_retry_count+1
                next_retry_at=NOW()+timedelta(seconds=settings.evaluation_provider_retry_delays[retry_count-1])
                result=self.evaluations.reschedule_transient_failure(value,exc.code,next_retry_at)
                log.warning("evaluation_rescheduled evaluation={} error_code={} http_status={} retry_count={} next_retry_at={} resume_phase={}", value.id, exc.code, exc.status, retry_count, next_retry_at.isoformat(), "adjudication" if value.audit_json else "candidate_audit")
                return result
            log.error("evaluation_retry_exhausted evaluation={} error_code={} http_status={} retry_count={}",value.id,exc.code,exc.status,value.provider_retry_count)
            return self.evaluations.fail(value,exc.code)
        except SQLAlchemyError:
            self.evaluations.db.rollback()
            log.exception("evaluation_database_error evaluation={}",value.id)
            raise
        except Exception:
            self.evaluations.db.rollback()
            log.exception("evaluation_failed evaluation={} error_code=INTERNAL_ERROR",value.id)
            return self.evaluations.fail(value,"INTERNAL_ERROR")
        finally:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError): await heartbeat

    async def _heartbeat(self, value):
        from app.core.config import settings
        interval=max(1, settings.evaluation_stale_seconds // 3)
        while True:
            await asyncio.sleep(interval)
            self.evaluations.heartbeat(value)

def public_evaluation(value):
    data={"status":value.status.value,"stage":value.stage.value,"progress":value.progress,
          "error_code":value.error_code,"max_score":20,"provider":value.provider,"model":value.model,
          "elapsed_ms":value.elapsed_ms,"started_at":value.started_at,"heartbeat_at":value.heartbeat_at,
          "provider_retry_count":value.provider_retry_count,"next_retry_at":value.next_retry_at}
    if value.provider == "huggingface" and value.model:
        from app.providers.llm import model_identity
        from app.core.config import settings
        data.update(model_family=settings.llm_model_family.value,inference_backend=model_identity(value.model)[1])
    if value.result_json: data.update(value.result_json)
    return data
