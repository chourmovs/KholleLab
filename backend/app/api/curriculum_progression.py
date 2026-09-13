from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.attempts import session as db_session
from app.schemas.curriculum_progression import CurriculumLevelChoice, CurriculumProgressSummary
from app.services.curriculum_progression import (CurriculumProgressionService,
                                                 InitialLevelAlreadySet,
                                                 LockedCurriculumLevel)
from app.services.learner_identity import learner_id

router = APIRouter(prefix="/curriculum-progress", tags=["curriculum-progress"])


def service(request: Request, db: Session) -> CurriculumProgressionService:
    return CurriculumProgressionService(db, request.app.state.problem_repository)


@router.get("", response_model=CurriculumProgressSummary)
def curriculum_progress(request: Request, db: Session = Depends(db_session)):
    return service(request, db).summary(learner_id(request))


@router.put("/current-level", response_model=CurriculumProgressSummary)
def set_current_level(body: CurriculumLevelChoice, request: Request,
                      db: Session = Depends(db_session)):
    progression = service(request, db)
    try:
        progression.set_current_level(learner_id(request), body.level.value)
    except LockedCurriculumLevel:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="curriculum_level_locked")
    return progression.summary(learner_id(request))


@router.put("/initial-level", response_model=CurriculumProgressSummary)
def set_initial_level(body: CurriculumLevelChoice, request: Request,
                      db: Session = Depends(db_session)):
    progression = service(request, db)
    try:
        progression.set_initial_level(learner_id(request), body.level.value)
    except InitialLevelAlreadySet:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="initial_level_already_set")
    return progression.summary(learner_id(request))
