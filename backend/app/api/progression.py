from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.attempts import session as db_session
from app.schemas.progression import ProgressionSummary
from app.services.learner_identity import learner_id
from app.services.progression import ProgressionService

router = APIRouter(prefix="/progression", tags=["progression"])


@router.get("", response_model=ProgressionSummary)
def progression(request: Request, db: Session = Depends(db_session)):
    return ProgressionService(db).summary(learner_id(request))
