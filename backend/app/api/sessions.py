import uuid
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.attempts import session as db_session
from app.models.attempt import Attempt, AttemptStatus, utcnow
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.models.tutor_assessment import TutorAssessmentRecord
from app.schemas.learning_session import SessionDetail, SessionStart, SessionSummary, SessionTransition
from app.schemas.tutor import TutorResourceRecommendation, TutorResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


def problem_payload(repository, problem_id: str):
    problem = repository.get(problem_id)
    if not problem:
        return None, f"Exercice indisponible ({problem_id})"
    data = problem.model_dump(mode="json") if hasattr(problem, "model_dump") else problem.dict()
    return data, problem.title


def latest_tutor(db: Session, attempt_ids: list[uuid.UUID]):
    if not attempt_ids:
        return None
    return db.scalars(select(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id.in_(attempt_ids)).order_by(TutorAssessmentRecord.created_at.desc())).first()


def serialize(value: LearningSession, request: Request, db: Session, detail=False):
    attempts = list(db.scalars(select(Attempt).where(Attempt.session_id == value.id).order_by(Attempt.started_at)))
    tutor = latest_tutor(db, [a.id for a in attempts])
    problem, title = problem_payload(request.app.state.problem_repository, value.problem_id)
    outcome = tutor.student_state if tutor else ("Travail soumis" if value.status == LearningSessionStatus.COMPLETED else None)
    base = dict(session_id=value.id, problem_id=value.problem_id, problem_title=title, status=value.status,
                created_at=value.created_at, updated_at=value.updated_at, started_at=value.started_at,
                completed_at=value.completed_at, duration_seconds=value.duration_seconds,
                number_of_attempts=len(attempts), number_of_tutor_interactions=db.scalar(select(func.count()).select_from(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id.in_([a.id for a in attempts]))) or 0,
                outcome=outcome)
    if not detail:
        return base
    assessment = None
    if tutor:
        resource = request.app.state.resource_repository.get(tutor.recommended_resource_id) if tutor.recommended_resource_id else None
        recommendation = TutorResourceRecommendation(id=resource.id, type=resource.type, title=resource.title, need=tutor.resource_need) if resource and tutor.resource_need else None
        assessment = TutorResponse(assessment_id=str(tutor.id), revision=tutor.revision, student_state=tutor.student_state,
            intervention_needed=tutor.intervention_needed, intervention_type=tutor.intervention_type,
            intervention=tutor.intervention, confidence=tutor.confidence, effective_help_level=tutor.effective_help_level,
            provider=tutor.provider, model=tutor.model, backend=tutor.backend, resource_recommendation=recommendation)
    recommendation = assessment.resource_recommendation.model_dump() if assessment and assessment.resource_recommendation else None
    final = attempts[-1].solution_markdown if attempts else ""
    return {**base, "problem": problem, "attempts": attempts, "current_attempt_id": value.current_attempt_id,
            "final_work": final, "tutor_assessment": assessment, "resource_recommendation": recommendation}


@router.post("", response_model=SessionDetail, status_code=201)
def start(body: SessionStart, request: Request, db: Session = Depends(db_session)):
    if not request.app.state.problem_repository.get(body.problem_id):
        return JSONResponse(status_code=404, content={"error": "problem_not_found", "message": "Problem does not exist."})
    if not body.force_new:
        existing = db.scalar(select(LearningSession).where(LearningSession.active_problem_key == body.problem_id))
        if existing:
            return serialize(existing, request, db, True)
    value = LearningSession(problem_id=body.problem_id, active_problem_key=body.problem_id)
    db.add(value)
    db.flush()
    attempt = Attempt(problem_id=body.problem_id, session_id=value.id)
    db.add(attempt)
    db.flush()
    value.current_attempt_id = attempt.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(LearningSession).where(LearningSession.active_problem_key == body.problem_id))
        if not existing:
            raise
        return serialize(existing, request, db, True)
    db.refresh(value)
    return serialize(value, request, db, True)


@router.get("", response_model=list[SessionSummary])
def history(request: Request, status: LearningSessionStatus | None = Query(None), problem_id: str | None = Query(None), db: Session = Depends(db_session)):
    query = select(LearningSession)
    if status:
        query = query.where(LearningSession.status == status)
    if problem_id:
        query = query.where(LearningSession.problem_id == problem_id)
    values = db.scalars(query.order_by(LearningSession.updated_at.desc(), LearningSession.created_at.desc())).all()
    return [serialize(value, request, db) for value in values]


@router.get("/active/latest", response_model=SessionDetail | None)
def active(request: Request, db: Session = Depends(db_session)):
    value = db.scalar(select(LearningSession).where(LearningSession.status == LearningSessionStatus.ACTIVE).order_by(LearningSession.updated_at.desc()))
    return serialize(value, request, db, True) if value else None


@router.get("/{session_id}", response_model=SessionDetail)
def detail(session_id: uuid.UUID, request: Request, db: Session = Depends(db_session)):
    value = db.get(LearningSession, session_id)
    return serialize(value, request, db, True) if value else JSONResponse(status_code=404, content={"error": "session_not_found"})


def transition(session_id, target, body, request, db):
    now = utcnow()
    values = {"status": target, "active_problem_key": None, "updated_at": now}
    if target == LearningSessionStatus.COMPLETED:
        values["completed_at"] = now
    result = db.execute(update(LearningSession).where(LearningSession.id == session_id, LearningSession.status == body.expected_status).values(**values))
    if result.rowcount != 1:
        db.rollback()
        value = db.get(LearningSession, session_id)
        code = 404 if value is None else 409
        return JSONResponse(status_code=code, content={"error": "session_not_found" if code == 404 else "session_not_active"})
    db.commit()
    value = db.get(LearningSession, session_id)
    return serialize(value, request, db, True)


@router.post("/{session_id}/complete", response_model=SessionDetail)
def complete(session_id: uuid.UUID, body: SessionTransition, request: Request, db: Session = Depends(db_session)):
    return transition(session_id, LearningSessionStatus.COMPLETED, body, request, db)


@router.post("/{session_id}/abandon", response_model=SessionDetail)
def abandon(session_id: uuid.UUID, body: SessionTransition, request: Request, db: Session = Depends(db_session)):
    return transition(session_id, LearningSessionStatus.ABANDONED, body, request, db)
