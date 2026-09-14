from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.attempts import session as db_session
from app.schemas.curriculum_progression import CurriculumLevelChoice, CurriculumProgressSummary
from app.services.curriculum_progression import (CurriculumProgressionService,
                                                 ActiveSessionExists,
                                                 AlreadyHighestCurriculum,
                                                 InvalidCurriculumState,
                                                 InitialLevelAlreadySet,
                                                 LockedCurriculumLevel,
                                                 NextLevelLocked,
                                                 OnboardingRequired)
from app.services.learner_identity import learner_id

router = APIRouter(prefix="/curriculum-progress", tags=["curriculum-progress"])


def service(request: Request, db: Session) -> CurriculumProgressionService:
    return CurriculumProgressionService(db, request.app.state.problem_repository)


@router.get("", response_model=CurriculumProgressSummary)
def curriculum_progress(request: Request, db: Session = Depends(db_session)):
    progression = service(request, db)
    try:
        result = progression.reconcile_unlocks(learner_id(request))
        db.commit()
        return progression.build_summary(learner_id(request), result.state)
    except InvalidCurriculumState:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid_curriculum_state")


ERRORS = {
    LockedCurriculumLevel: "curriculum_level_locked",
    ActiveSessionExists: "active_session_exists",
    NextLevelLocked: "next_level_locked",
    AlreadyHighestCurriculum: "already_highest_curriculum",
    OnboardingRequired: "onboarding_required",
    InvalidCurriculumState: "invalid_curriculum_state",
    InitialLevelAlreadySet: "initial_level_already_set",
}


def mutate_and_summarize(progression, db, owner, operation):
    try:
        state = operation()
        db.commit()
        return progression.build_summary(owner, state)
    except tuple(ERRORS) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=ERRORS[type(exc)])


@router.put("/current-level", response_model=CurriculumProgressSummary)
def set_current_level(body: CurriculumLevelChoice, request: Request,
                      db: Session = Depends(db_session)):
    progression = service(request, db)
    owner = learner_id(request)
    return mutate_and_summarize(progression, db, owner,
                                lambda: progression.set_current_level(owner, body.level.value))


@router.post("/advance", response_model=CurriculumProgressSummary)
def advance(request: Request, db: Session = Depends(db_session)):
    progression = service(request, db)
    owner = learner_id(request)
    return mutate_and_summarize(progression, db, owner,
                                lambda: progression.advance(owner))


@router.put("/initial-level", response_model=CurriculumProgressSummary)
def set_initial_level(body: CurriculumLevelChoice, request: Request,
                      db: Session = Depends(db_session)):
    progression = service(request, db)
    owner = learner_id(request)
    return mutate_and_summarize(progression, db, owner,
                                lambda: progression.set_initial_level(owner, body.level.value))
