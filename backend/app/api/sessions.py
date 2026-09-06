import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.attempts import session as db_session
from app.models.attempt import Attempt, utcnow
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.models.tutor_assessment import TutorAssessmentRecord
from app.schemas.learning_session import SessionDetail, SessionStart, SessionSummary, SessionTransition
from app.schemas.problem import to_public_problem_detail
from app.schemas.tutor import TutorResourceRecommendation, TutorResponse
from app.services.learner_identity import learner_id

router = APIRouter(prefix="/sessions", tags=["sessions"])


def problem_payload(repository, problem_id: str):
    problem = repository.get(problem_id)
    if not problem:
        return None, f"Exercice indisponible ({problem_id})"
    return to_public_problem_detail(problem), problem.title


def load_related(db: Session, values: list[LearningSession]):
    session_ids = [value.id for value in values]
    attempts_by_session: dict[uuid.UUID, list[Attempt]] = defaultdict(list)
    tutors_by_attempt: dict[uuid.UUID, list[TutorAssessmentRecord]] = defaultdict(list)
    if not session_ids:
        return attempts_by_session, tutors_by_attempt
    attempts = list(db.scalars(select(Attempt).where(Attempt.session_id.in_(session_ids)).order_by(Attempt.started_at)))
    for attempt in attempts:
        attempts_by_session[attempt.session_id].append(attempt)
    attempt_ids = [attempt.id for attempt in attempts]
    if attempt_ids:
        tutors = db.scalars(select(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id.in_(attempt_ids)).order_by(TutorAssessmentRecord.created_at.desc()))
        for tutor in tutors:
            tutors_by_attempt[tutor.attempt_id].append(tutor)
    return attempts_by_session, tutors_by_attempt


def serialize(value: LearningSession, request: Request, attempts_by_session, tutors_by_attempt, detail=False):
    attempts = attempts_by_session[value.id]
    tutors = [tutor for attempt in attempts for tutor in tutors_by_attempt[attempt.id]]
    tutor = max(tutors, key=lambda item: item.created_at) if tutors else None
    problem, title = problem_payload(request.app.state.problem_repository, value.problem_id)
    outcome = tutor.student_state if tutor else ("Travail soumis" if value.status == LearningSessionStatus.COMPLETED else None)
    base = dict(session_id=value.id, problem_id=value.problem_id, problem_title=title, status=value.status,
                created_at=value.created_at, updated_at=value.updated_at, started_at=value.started_at,
                completed_at=value.completed_at, duration_seconds=value.duration_seconds,
                number_of_attempts=len(attempts), number_of_tutor_interactions=len(tutors), outcome=outcome)
    if not detail:
        return base
    # Never trust a dangling/cross-session current_attempt_id.
    current_attempt_id = value.current_attempt_id if any(a.id == value.current_attempt_id for a in attempts) else None
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
    return {**base, "problem": problem, "attempts": attempts, "current_attempt_id": current_attempt_id,
            "final_work": final, "tutor_assessment": assessment, "resource_recommendation": recommendation}


def serialize_many(values, request, db, detail=False):
    attempts, tutors = load_related(db, values)
    return [serialize(value, request, attempts, tutors, detail) for value in values]


@router.post("", response_model=SessionDetail, status_code=201)
def start(body: SessionStart, request: Request, db: Session = Depends(db_session)):
    owner = learner_id(request)
    if not request.app.state.problem_repository.get(body.problem_id):
        return JSONResponse(status_code=404, content={"error": "problem_not_found", "message": "Problem does not exist."})
    active_query = select(LearningSession).where(LearningSession.learner_id == owner, LearningSession.active_problem_key == body.problem_id)
    existing = db.scalar(active_query)
    # force_new never supersedes an active session: that would violate uniqueness and lose work.
    if existing:
        return serialize_many([existing], request, db, True)[0]
    value = LearningSession(problem_id=body.problem_id, learner_id=owner, active_problem_key=body.problem_id)
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
        existing = db.scalar(active_query)
        if not existing:
            raise
        return serialize_many([existing], request, db, True)[0]
    db.refresh(value)
    return serialize_many([value], request, db, True)[0]


@router.get("", response_model=list[SessionSummary])
def history(request: Request, status: LearningSessionStatus | None = Query(None), problem_id: str | None = Query(None),
            limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(db_session)):
    query = select(LearningSession).where(LearningSession.learner_id == learner_id(request))
    if status:
        query = query.where(LearningSession.status == status)
    if problem_id:
        query = query.where(LearningSession.problem_id == problem_id)
    values = list(db.scalars(query.order_by(LearningSession.updated_at.desc(), LearningSession.created_at.desc(), LearningSession.id.desc()).offset(offset).limit(limit)))
    return serialize_many(values, request, db)


@router.get("/active/latest", response_model=SessionDetail | None)
def active(request: Request, db: Session = Depends(db_session)):
    value = db.scalar(select(LearningSession).where(LearningSession.learner_id == learner_id(request), LearningSession.status == LearningSessionStatus.ACTIVE).order_by(LearningSession.updated_at.desc(), LearningSession.created_at.desc(), LearningSession.id.desc()))
    return serialize_many([value], request, db, True)[0] if value else None


@router.get("/{session_id}", response_model=SessionDetail)
def detail(session_id: uuid.UUID, request: Request, db: Session = Depends(db_session)):
    value = db.scalar(select(LearningSession).where(LearningSession.id == session_id, LearningSession.learner_id == learner_id(request)))
    return serialize_many([value], request, db, True)[0] if value else JSONResponse(status_code=404, content={"error": "session_not_found"})


def transition(session_id, target, request, db):
    owner = learner_id(request)
    now = utcnow()
    values = {"status": target, "active_problem_key": None, "updated_at": now}
    if target == LearningSessionStatus.COMPLETED:
        values["completed_at"] = now
    result = db.execute(update(LearningSession).where(LearningSession.id == session_id, LearningSession.learner_id == owner,
                                                        LearningSession.status == LearningSessionStatus.ACTIVE).values(**values))
    if result.rowcount != 1:
        db.rollback()
        owned = db.scalar(select(LearningSession.id).where(LearningSession.id == session_id, LearningSession.learner_id == owner))
        code = 404 if owned is None else 409
        return JSONResponse(status_code=code, content={"error": "session_not_found" if code == 404 else "session_not_active"})
    db.commit()
    value = db.scalar(select(LearningSession).where(LearningSession.id == session_id, LearningSession.learner_id == owner))
    return serialize_many([value], request, db, True)[0]


@router.post("/{session_id}/complete", response_model=SessionDetail)
def complete(session_id: uuid.UUID, body: SessionTransition, request: Request, db: Session = Depends(db_session)):
    return transition(session_id, LearningSessionStatus.COMPLETED, request, db)


@router.post("/{session_id}/abandon", response_model=SessionDetail)
def abandon(session_id: uuid.UUID, body: SessionTransition, request: Request, db: Session = Depends(db_session)):
    return transition(session_id, LearningSessionStatus.ABANDONED, request, db)
