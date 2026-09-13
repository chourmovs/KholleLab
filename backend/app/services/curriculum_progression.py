import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.problem import CURRICULUM_ORDER, CurriculumLevel
from app.models.attempt import Attempt, utcnow
from app.models.curriculum_state import LearnerCurriculumState
from app.models.evaluation import Evaluation
from app.models.learning_session import LearningSession
from app.services.evidence import EvidenceKind, classify_evidence


NEXT_LEVEL_UNLOCK_RATIO = 0.60
DEFAULT_CURRICULUM_LEVEL = CURRICULUM_ORDER[0]


class LockedCurriculumLevel(ValueError):
    pass


class InitialLevelAlreadySet(ValueError):
    pass


class CurriculumProgressionService:
    """Persistent school-level progression, deliberately independent from XP."""

    def __init__(self, db: Session, problem_repository):
        self.db = db
        self.problems = problem_repository

    def _bootstrap_level(self, learner_id: uuid.UUID) -> str:
        sessions = list(self.db.scalars(select(LearningSession).where(
            LearningSession.learner_id == learner_id,
        ).order_by(LearningSession.updated_at.desc(), LearningSession.id.desc())))
        resolved = self.problems.get_many((item.problem_id for item in sessions), self.db)
        for item in sessions:
            snapshot_level = (item.curriculum_snapshot or {}).get("level")
            if snapshot_level in CURRICULUM_ORDER:
                return snapshot_level
            problem = resolved.get(item.problem_id)
            if problem:
                return problem.curriculum.level.value
        return DEFAULT_CURRICULUM_LEVEL

    def get_or_create_state(self, learner_id: uuid.UUID) -> LearnerCurriculumState:
        existing = self.db.get(LearnerCurriculumState, learner_id)
        if existing:
            return existing
        level = self._bootstrap_level(learner_id)
        value = LearnerCurriculumState(
            learner_id=learner_id, initial_level=level, current_level=level,
            highest_unlocked_level=level, onboarding_completed=False,
        )
        try:
            # The primary key is the final guard when concurrent first requests race.
            with self.db.begin_nested():
                self.db.add(value)
                self.db.flush()
            return value
        except IntegrityError:
            return self.db.get(LearnerCurriculumState, learner_id)

    def eligible_problem_ids(self, level: str) -> set[str]:
        CurriculumLevel(level)
        # Only the validated stable shared corpus is a denominator. Runtime LLM
        # materializations are intentionally excluded so generation cannot dilute progress.
        source = self.problems.list_static() if hasattr(self.problems, "list_static") else self.problems.list()
        return {problem.id for problem in source if problem.curriculum.level.value == level}

    def solved_problem_ids(self, learner_id: uuid.UUID, level: str) -> set[str]:
        eligible = self.eligible_problem_ids(level)
        if not eligible:
            return set()
        rows = self.db.execute(select(LearningSession.problem_id, LearningSession.status, Evaluation).join(
            Attempt, Attempt.session_id == LearningSession.id,
        ).join(Evaluation, Evaluation.attempt_id == Attempt.id).where(
            LearningSession.learner_id == learner_id,
            LearningSession.problem_id.in_(eligible),
        )).all()
        return {problem_id for problem_id, status, evaluation in rows
                if classify_evidence(status, evaluation) == EvidenceKind.POSITIVE}

    def level_progress(self, learner_id: uuid.UUID, level: str) -> dict:
        CurriculumLevel(level)
        eligible_ids = self.eligible_problem_ids(level)
        solved = len(self.solved_problem_ids(learner_id, level))
        eligible = len(eligible_ids)
        progress = solved / eligible if eligible else 0.0
        return {"level": level, "eligible": eligible, "solved": solved, "progress": progress,
                "progress_percent": progress * 100}

    def refresh_unlocks(self, learner_id: uuid.UUID) -> LearnerCurriculumState:
        state = self.get_or_create_state(learner_id)
        highest = CURRICULUM_ORDER.index(state.highest_unlocked_level)
        # Unlock sequentially from every currently unlocked level. Persistent maximum
        # means corpus growth can never take access away.
        while highest < len(CURRICULUM_ORDER) - 1:
            progress = self.level_progress(learner_id, CURRICULUM_ORDER[highest])
            if progress["eligible"] == 0 or progress["progress"] < NEXT_LEVEL_UNLOCK_RATIO:
                break
            highest += 1
            state.highest_unlocked_level = CURRICULUM_ORDER[highest]
            state.updated_at = utcnow()
        self.db.flush()
        return state

    def summary(self, learner_id: uuid.UUID) -> dict:
        state = self.refresh_unlocks(learner_id)
        highest = CURRICULUM_ORDER.index(state.highest_unlocked_level)
        levels = []
        for index, level in enumerate(CURRICULUM_ORDER):
            item = self.level_progress(learner_id, level)
            item.update(unlocked=index <= highest, current=level == state.current_level)
            levels.append(item)
        self.db.commit()
        return {"initial_level": state.initial_level, "current_level": state.current_level,
                "highest_unlocked_level": state.highest_unlocked_level,
                "onboarding_completed": state.onboarding_completed,
                "unlock_ratio": NEXT_LEVEL_UNLOCK_RATIO, "levels": levels}

    def set_initial_level(self, learner_id: uuid.UUID, level: str) -> LearnerCurriculumState:
        CurriculumLevel(level)
        state = self.get_or_create_state(learner_id)
        if state.onboarding_completed and state.initial_level != level:
            raise InitialLevelAlreadySet(level)
        if not state.onboarding_completed:
            state.initial_level = state.current_level = state.highest_unlocked_level = level
            state.onboarding_completed = True
            state.updated_at = utcnow()
        self.db.commit()
        return state

    def set_current_level(self, learner_id: uuid.UUID, level: str) -> LearnerCurriculumState:
        CurriculumLevel(level)
        state = self.refresh_unlocks(learner_id)
        if CURRICULUM_ORDER.index(level) > CURRICULUM_ORDER.index(state.highest_unlocked_level):
            raise LockedCurriculumLevel(level)
        state.current_level = level
        state.updated_at = utcnow()
        self.db.commit()
        return state
