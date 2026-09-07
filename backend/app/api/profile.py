from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.attempts import session as db_session
from app.schemas.profile import LearnerProfileResponse
from app.services.learner_identity import learner_id
from app.services.learner_profile import LearnerProfileBuilder

router=APIRouter(prefix="/profile",tags=["profile"])

@router.get("",response_model=LearnerProfileResponse)
def profile(request:Request,db:Session=Depends(db_session)):
    return LearnerProfileBuilder(db,request.app.state.problem_repository).build(learner_id(request))
