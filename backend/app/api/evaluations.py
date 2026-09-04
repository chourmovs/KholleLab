import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.attempts import session, error
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.providers.llm import provider_from_settings
from app.services.examiner import *

router=APIRouter(prefix="/attempts",tags=["evaluations"])
def service(request,db): return ExaminerService(AttemptRepository(db),EvaluationRepository(db),request.app.state.problem_repository,provider_from_settings())
def failure(exc):
    if isinstance(exc,ExaminerAttemptNotFound): return error("attempt_not_found","Attempt does not exist.",404)
    if isinstance(exc,AttemptNotSubmitted): return error("attempt_not_submitted","Only submitted attempts can be evaluated.",409)
    if isinstance(exc,EvaluationNotFound): return error("evaluation_not_found","Evaluation does not exist.",404)
    return error("retry_not_allowed","Only failed evaluations can be retried.",409)

@router.post("/{attempt_id}/evaluation")
async def evaluate(attempt_id:uuid.UUID,request:Request,db:Session=Depends(session)):
    try: return public_evaluation(await service(request,db).evaluate_attempt(attempt_id))
    except (ExaminerAttemptNotFound,AttemptNotSubmitted,ExaminerProblemNotFound) as exc: return failure(exc)
@router.get("/{attempt_id}/evaluation")
def get_evaluation(attempt_id:uuid.UUID,db:Session=Depends(session)):
    if not AttemptRepository(db).get(attempt_id): return error("attempt_not_found","Attempt does not exist.",404)
    value=EvaluationRepository(db).get_for_attempt(attempt_id)
    return public_evaluation(value) if value else error("evaluation_not_found","Evaluation does not exist.",404)
@router.post("/{attempt_id}/evaluation/retry")
async def retry(attempt_id:uuid.UUID,request:Request,db:Session=Depends(session)):
    try: return public_evaluation(await service(request,db).evaluate_attempt(attempt_id,retry=True))
    except (ExaminerAttemptNotFound,AttemptNotSubmitted,EvaluationNotFound,RetryNotAllowed) as exc: return failure(exc)
