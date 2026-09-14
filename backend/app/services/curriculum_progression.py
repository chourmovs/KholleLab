import math
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.problem import CURRICULUM_ORDER, CurriculumLevel, progression_unit_id
from app.models.attempt import Attempt, utcnow
from app.models.curriculum_state import LearnerCurriculumState
from app.models.evaluation import Evaluation
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.services.evidence import EvidenceKind, classify_evidence


NEXT_LEVEL_UNLOCK_RATIO = 0.60
DEFAULT_CURRICULUM_LEVEL = CURRICULUM_ORDER[0]


def curriculum_index(level: str) -> int:
    """Return the canonical ordering index, rejecting corrupt/unknown values."""
    try:
        return CURRICULUM_ORDER.index(level)
    except ValueError as exc:
        raise InvalidCurriculumState(level) from exc


def previous_curriculum_level(level: str) -> str | None:
    index = curriculum_index(level)
    return CURRICULUM_ORDER[index - 1] if index else None


def next_curriculum_level(level: str) -> str | None:
    index = curriculum_index(level) + 1
    return CURRICULUM_ORDER[index] if index < len(CURRICULUM_ORDER) else None


class CurriculumProgressionError(ValueError):
    pass


class LockedCurriculumLevel(CurriculumProgressionError):
    pass


class InitialLevelAlreadySet(CurriculumProgressionError):
    pass


class ActiveSessionExists(CurriculumProgressionError):
    pass


class NextLevelLocked(CurriculumProgressionError):
    pass


class AlreadyHighestCurriculum(CurriculumProgressionError):
    pass


class OnboardingRequired(CurriculumProgressionError):
    pass


class InvalidCurriculumState(CurriculumProgressionError):
    pass


@dataclass(frozen=True)
class UnlockRefreshResult:
    state: LearnerCurriculumState
    previous_highest_unlocked_level: str
    highest_unlocked_level: str
    newly_unlocked_levels: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.newly_unlocked_levels)

    @property
    def current_level(self) -> str:
        """Small compatibility bridge for callers that formerly received state."""
        return self.state.current_level


class CurriculumProgressionService:
    """Persistent curriculum progression. Callers own commit/rollback boundaries."""

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

    def get_or_create_state(self, learner_id: uuid.UUID, *, for_update: bool = False) -> LearnerCurriculumState:
        query = select(LearnerCurriculumState).where(
            LearnerCurriculumState.learner_id == learner_id)
        existing = self.db.scalar(query.with_for_update() if for_update else query)
        if existing:
            return existing
        level = self._bootstrap_level(learner_id)
        value = LearnerCurriculumState(
            learner_id=learner_id, initial_level=level, current_level=level,
            highest_unlocked_level=level, onboarding_completed=False,
        )
        try:
            with self.db.begin_nested():
                self.db.add(value)
                self.db.flush()
            return value
        except IntegrityError:
            # The primary key serializes concurrent first requests.
            return self.db.scalar(query.with_for_update() if for_update else query)

    def _validate_state(self, state: LearnerCurriculumState) -> None:
        initial = curriculum_index(state.initial_level)
        current = curriculum_index(state.current_level)
        highest = curriculum_index(state.highest_unlocked_level)
        if highest < initial or current > highest:
            raise InvalidCurriculumState("inconsistent curriculum high-water mark")

    def _level_problems(self, level: str):
        CurriculumLevel(level)
        source = self.problems.list_static() if hasattr(self.problems, "list_static") else self.problems.list()
        return [problem for problem in source if problem.curriculum.level.value == level]

    def eligible_progression_units(self, level: str) -> set[str]:
        """Return pedagogical units in the validated static corpus for one level."""
        return {progression_unit_id(problem) for problem in self._level_problems(level)}

    def solved_progression_units(self, learner_id: uuid.UUID, level: str) -> set[str]:
        """Return level-local units having at least one canonical positive evaluation."""
        level_problems = self._level_problems(level)
        units_by_problem = {problem.id: progression_unit_id(problem) for problem in level_problems}
        if not units_by_problem:
            return set()
        rows = self.db.execute(select(LearningSession.problem_id, LearningSession.status, Evaluation).join(
            Attempt, Attempt.session_id == LearningSession.id,
        ).join(Evaluation, Evaluation.attempt_id == Attempt.id).where(
            LearningSession.learner_id == learner_id,
            LearningSession.problem_id.in_(units_by_problem),
        )).all()
        return {units_by_problem[problem_id] for problem_id, status, evaluation in rows
                if classify_evidence(status, evaluation) == EvidenceKind.POSITIVE}

    def level_progress(self, learner_id: uuid.UUID, level: str) -> dict:
        eligible_units = self.eligible_progression_units(level)
        solved = len(self.solved_progression_units(learner_id, level))
        eligible = len(eligible_units)
        progress = solved / eligible if eligible else 0.0
        return {"level": level, "eligible": eligible, "solved": solved,
                "progress": progress, "progress_percent": progress * 100}

    def refresh_unlocks(self, learner_id: uuid.UUID) -> UnlockRefreshResult:
        """Lock and advance the durable high-water mark, without committing."""
        state = self.get_or_create_state(learner_id, for_update=True)
        self._validate_state(state)
        previous = state.highest_unlocked_level
        newly_unlocked = []
        while (successor := next_curriculum_level(state.highest_unlocked_level)) is not None:
            progress = self.level_progress(learner_id, state.highest_unlocked_level)
            if (progress["eligible"] == 0
                    or progress["solved"] < math.ceil(progress["eligible"] * NEXT_LEVEL_UNLOCK_RATIO)):
                break
            state.highest_unlocked_level = successor
            state.updated_at = utcnow()
            newly_unlocked.append(successor)
        self.db.flush()
        return UnlockRefreshResult(state, previous, state.highest_unlocked_level,
                                   tuple(newly_unlocked))

    def reconcile_unlocks(self, learner_id: uuid.UUID) -> UnlockRefreshResult:
        """Explicit legacy-history reconciliation entry point."""
        return self.refresh_unlocks(learner_id)

    def build_summary(self, learner_id: uuid.UUID, state: LearnerCurriculumState) -> dict:
        """Build a read model without mutating or committing."""
        self._validate_state(state)
        highest = curriculum_index(state.highest_unlocked_level)
        levels = []
        by_level = {}
        for index, level in enumerate(CURRICULUM_ORDER):
            item = self.level_progress(learner_id, level)
            item.update(unlocked=index <= highest, current=level == state.current_level)
            levels.append(item)
            by_level[level] = item
        current = by_level[state.current_level]
        successor = next_curriculum_level(state.current_level)
        next_unlocked = successor is not None and curriculum_index(successor) <= highest
        required = math.ceil(current["eligible"] * NEXT_LEVEL_UNLOCK_RATIO)
        remaining = (max(0, required - current["solved"])
                     if successor is not None and not next_unlocked and current["eligible"] else 0)
        return {
            "initial_level": state.initial_level,
            "current_level": state.current_level,
            "highest_unlocked_level": state.highest_unlocked_level,
            "onboarding_completed": state.onboarding_completed,
            "unlock_ratio": NEXT_LEVEL_UNLOCK_RATIO,
            "current": {key: current[key] for key in
                        ("level", "eligible", "solved", "progress", "progress_percent")},
            "next_level": successor,
            "next_level_unlocked": next_unlocked,
            "can_advance": bool(state.onboarding_completed and next_unlocked),
            "remaining_to_unlock": remaining,
            "levels": levels,
        }

    def summary(self, learner_id: uuid.UUID) -> dict:
        """Compatibility convenience; deliberately never commits."""
        result = self.reconcile_unlocks(learner_id)
        return self.build_summary(learner_id, result.state)

    def _require_no_active_session(self, learner_id: uuid.UUID) -> None:
        active = self.db.scalar(select(LearningSession.id).where(
            LearningSession.learner_id == learner_id,
            LearningSession.status == LearningSessionStatus.ACTIVE,
        ).limit(1))
        if active is not None:
            raise ActiveSessionExists

    def set_initial_level(self, learner_id: uuid.UUID, level: str) -> LearnerCurriculumState:
        CurriculumLevel(level)
        state = self.get_or_create_state(learner_id, for_update=True)
        self._validate_state(state)
        if state.onboarding_completed and state.initial_level != level:
            raise InitialLevelAlreadySet(level)
        if not state.onboarding_completed:
            self._require_no_active_session(learner_id)
            state.initial_level = state.current_level = state.highest_unlocked_level = level
            state.onboarding_completed = True
            state.updated_at = utcnow()
            self.db.flush()
        return state

    def set_current_level(self, learner_id: uuid.UUID, level: str) -> LearnerCurriculumState:
        CurriculumLevel(level)
        state = self.refresh_unlocks(learner_id).state
        if curriculum_index(level) > curriculum_index(state.highest_unlocked_level):
            raise LockedCurriculumLevel(level)
        if state.current_level != level:
            self._require_no_active_session(learner_id)
            state.current_level = level
            state.updated_at = utcnow()
            self.db.flush()
        return state

    def advance(self, learner_id: uuid.UUID) -> LearnerCurriculumState:
        state = self.refresh_unlocks(learner_id).state
        if not state.onboarding_completed:
            raise OnboardingRequired
        successor = next_curriculum_level(state.current_level)
        if successor is None:
            raise AlreadyHighestCurriculum
        if curriculum_index(successor) > curriculum_index(state.highest_unlocked_level):
            raise NextLevelLocked
        self._require_no_active_session(learner_id)
        state.current_level = successor
        state.updated_at = utcnow()
        self.db.flush()
        return state
