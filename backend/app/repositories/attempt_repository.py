import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.attempt import Attempt, AttemptStatus, utcnow
from app.models.learning_session import LearningSession, LearningSessionStatus


class AttemptError(Exception):
    pass


class AttemptNotFound(AttemptError):
    pass


class AttemptConflict(AttemptError):
    def __init__(self, expected_revision: int, current_revision: int):
        self.expected_revision = expected_revision
        self.current_revision = current_revision


class AttemptAlreadySubmitted(AttemptError):
    pass


class AttemptRepository:
    def __init__(self, session: Session): self.session = session

    def create(self, problem_id: str) -> Attempt:
        attempt = Attempt(problem_id=problem_id)
        self.session.add(attempt); self.session.commit(); self.session.refresh(attempt)
        return attempt

    def get(self, attempt_id: uuid.UUID) -> Attempt | None:
        return self.session.get(Attempt, attempt_id)

    def _checked(self, attempt_id: uuid.UUID, expected_revision: int) -> Attempt:
        attempt = self.get(attempt_id)
        if attempt is None: raise AttemptNotFound
        if attempt.status == AttemptStatus.SUBMITTED: raise AttemptAlreadySubmitted
        if attempt.revision != expected_revision: raise AttemptConflict(expected_revision, attempt.revision)
        return attempt

    def save_solution(self, attempt_id: uuid.UUID, solution_markdown: str, elapsed_seconds: int, expected_revision: int) -> Attempt:
        self._checked(attempt_id, expected_revision)
        result = self.session.execute(update(Attempt).where(Attempt.id == attempt_id, Attempt.revision == expected_revision, Attempt.status == AttemptStatus.DRAFT).values(solution_markdown=solution_markdown, elapsed_seconds=elapsed_seconds, updated_at=utcnow(), revision=Attempt.revision + 1))
        if result.rowcount != 1:
            self.session.rollback(); current = self.get(attempt_id)
            if current is None: raise AttemptNotFound
            if current.status == AttemptStatus.SUBMITTED: raise AttemptAlreadySubmitted
            raise AttemptConflict(expected_revision, current.revision)
        attempt = self.get(attempt_id)
        if attempt and attempt.session_id:
            learning = self.session.get(LearningSession, attempt.session_id)
            if learning and learning.status == LearningSessionStatus.ACTIVE:
                learning.updated_at = attempt.updated_at
                learning.duration_seconds = elapsed_seconds
        self.session.commit(); return self.get(attempt_id)  # type: ignore[return-value]

    def submit(self, attempt_id: uuid.UUID, expected_revision: int) -> Attempt:
        self._checked(attempt_id, expected_revision); now = utcnow()
        result = self.session.execute(update(Attempt).where(Attempt.id == attempt_id, Attempt.revision == expected_revision, Attempt.status == AttemptStatus.DRAFT).values(status=AttemptStatus.SUBMITTED, submitted_at=now, updated_at=now, revision=Attempt.revision + 1))
        if result.rowcount != 1:
            self.session.rollback(); current = self.get(attempt_id)
            if current is None: raise AttemptNotFound
            if current.status == AttemptStatus.SUBMITTED: raise AttemptAlreadySubmitted
            raise AttemptConflict(expected_revision, current.revision)
        attempt = self.get(attempt_id)
        if attempt and attempt.session_id:
            learning = self.session.get(LearningSession, attempt.session_id)
            if learning and learning.status == LearningSessionStatus.ACTIVE:
                learning.status = LearningSessionStatus.COMPLETED
                learning.active_problem_key = None
                learning.completed_at = now
                learning.updated_at = now
                learning.duration_seconds = attempt.elapsed_seconds
        self.session.commit(); return self.get(attempt_id)  # type: ignore[return-value]
