import uuid
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.repositories.attempt_repository import AttemptAlreadySubmitted, AttemptConflict, AttemptNotFound, AttemptRepository
from app.schemas.attempt import AttemptCreate, AttemptResponse, AttemptSubmit, AttemptUpdate
from app.services.attempt_service import AttemptService, ProblemNotFound

router = APIRouter(prefix="/attempts", tags=["attempts"])
def session():
    db = SessionLocal()
    try: yield db
    finally: db.close()
def error(code: str, message: str, status_code: int, **extra): return JSONResponse(status_code=status_code, content={"error": code, "message": message, **extra})

@router.post("", response_model=AttemptResponse, status_code=status.HTTP_201_CREATED)
def create(body: AttemptCreate, request: Request, db: Session = Depends(session)):
    try: return AttemptService(AttemptRepository(db), request.app.state.problem_repository).create(body.problem_id)
    except ProblemNotFound: return error("problem_not_found", "Problem does not exist.", 404)

@router.get("/{attempt_id}", response_model=AttemptResponse)
def get(attempt_id: uuid.UUID, db: Session = Depends(session)):
    value = AttemptRepository(db).get(attempt_id)
    return value if value else error("attempt_not_found", "Attempt does not exist.", 404)

def domain_error(exc):
    if isinstance(exc, AttemptNotFound): return error("attempt_not_found", "Attempt does not exist.", 404)
    if isinstance(exc, AttemptAlreadySubmitted): return error("attempt_submitted", "Submitted attempts cannot be modified.", 409)
    return error("attempt_conflict", f"Attempt has been modified since revision {exc.expected_revision}.", 409, current_revision=exc.current_revision)

@router.patch("/{attempt_id}", response_model=AttemptResponse)
def patch(attempt_id: uuid.UUID, body: AttemptUpdate, db: Session = Depends(session)):
    try: return AttemptRepository(db).save_solution(attempt_id, body.solution_markdown, body.elapsed_seconds, body.expected_revision)
    except (AttemptNotFound, AttemptAlreadySubmitted, AttemptConflict) as exc: return domain_error(exc)

@router.post("/{attempt_id}/submit", response_model=AttemptResponse)
def submit(attempt_id: uuid.UUID, body: AttemptSubmit, db: Session = Depends(session)):
    try: return AttemptRepository(db).submit(attempt_id, body.expected_revision)
    except (AttemptNotFound, AttemptAlreadySubmitted, AttemptConflict) as exc: return domain_error(exc)
