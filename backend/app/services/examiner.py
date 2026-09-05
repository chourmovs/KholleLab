import json, time, uuid
from pathlib import Path
from app.models.attempt import AttemptStatus
from app.models.evaluation import EvaluationStatus
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas.evaluation import CandidateAudit, EvaluationResult
from app.providers.llm import LocalLLMError
from app.core.logging import component_logger

log=component_logger("examiner"); PROMPT_VERSION="examiner-v1"
class AttemptNotSubmitted(Exception): pass
class EvaluationNotFound(Exception): pass
class RetryNotAllowed(Exception): pass
class ExaminerAttemptNotFound(Exception): pass
class ExaminerProblemNotFound(Exception): pass

class ExaminerService:
    def __init__(self, attempts:AttemptRepository, evaluations:EvaluationRepository, problems, provider):
        self.attempts=attempts; self.evaluations=evaluations; self.problems=problems; self.provider=provider
    def _prompt(self,name): return (Path(__file__).parent.parent/"prompts"/name).read_text()
    async def evaluate_attempt(self, attempt_id:uuid.UUID, retry=False):
        attempt=self.attempts.get(attempt_id)
        if not attempt: raise ExaminerAttemptNotFound
        if attempt.status != AttemptStatus.SUBMITTED: raise AttemptNotSubmitted
        problem=self.problems.get(attempt.problem_id)
        if not problem: raise ExaminerProblemNotFound
        value=self.evaluations.get_for_attempt(attempt_id)
        if value:
            if retry:
                if value.status != EvaluationStatus.FAILED: raise RetryNotAllowed
                self.evaluations.restart(value)
            else: return value
        else:
            if retry: raise EvaluationNotFound
            value=self.evaluations.create_running(attempt_id,self.provider.name,self.provider.model,PROMPT_VERSION)
        started=time.perf_counter(); log.info("Evaluation started attempt={} provider={} model={}",attempt_id,self.provider.name,self.provider.model)
        candidate=f"<problem>\n{problem.statement}\n</problem>\n<candidate_solution>\n{attempt.solution_markdown}\n</candidate_solution>"
        try:
            log.info("Evaluation pass started attempt={} pass=1", attempt_id)
            audit=await self.provider.structured_response(instructions=self._prompt("examiner_audit_v1.md"),input_text=candidate,response_model=CandidateAudit)
            log.info("Structured parsing success attempt={} pass=1", attempt_id)
            adjudication=candidate+f"\n<candidate_audit>\n{json.dumps(audit.model_dump(mode='json'),ensure_ascii=False)}\n</candidate_audit>\n<reference_solution>\n{problem.reference_solution}\n</reference_solution>"
            log.info("Evaluation pass started attempt={} pass=2", attempt_id)
            result=await self.provider.structured_response(instructions=self._prompt("examiner_adjudication_v1.md"),input_text=adjudication,response_model=EvaluationResult)
            result=EvaluationResult.model_validate(result)
            value=self.evaluations.complete(value,audit,result); log.info("Evaluation completed attempt={} provider={} model={} elapsed_ms={:.1f}",attempt_id,self.provider.name,self.provider.model,(time.perf_counter()-started)*1000); return value
        except Exception as exc:
            codes={"timeout":"local_llm_timeout","dns_error":"local_llm_unavailable","connection_refused":"local_llm_unavailable","http_4xx":"local_llm_http_error","http_5xx":"local_llm_http_error","invalid_json":"local_llm_invalid_json","invalid_structured_output":"local_llm_schema_error","empty_response":"local_llm_schema_error"}
            code=codes.get(exc.code,"local_llm_unavailable") if isinstance(exc,LocalLLMError) else "provider_error"
            log.exception("Evaluation failed attempt={} provider={} model={} error_code={} elapsed_ms={:.1f}",attempt_id,self.provider.name,self.provider.model,code,(time.perf_counter()-started)*1000)
            return self.evaluations.fail(value,code)

def public_evaluation(value):
    data={"status":value.status.value,"error_code":value.error_code,"max_score":20,"provider":value.provider,"model":value.model}
    if value.result_json: data.update(value.result_json)
    return data
