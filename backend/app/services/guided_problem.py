"""Deterministic, static-corpus next-exercise policy."""
import uuid

from sqlalchemy import select

from app.domain.problem import CurriculumLevel
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.services.adaptive_context import AdaptiveContextBuilder
from app.services.adaptive_selection import AdaptiveSelectionService
from app.services.curriculum_progression import CurriculumProgressionService
from app.services.evidence import EvidenceKind
from app.services.problem_selector import ProblemSelector


class OnboardingRequired(Exception): pass
class GuidedProblemUnavailable(Exception): pass
class CurrentLevelInvalid(Exception): pass


class GuidedProblemService:
    def __init__(self, db, catalog):
        self.db, self.catalog = db, catalog
        self.progression = CurriculumProgressionService(db, catalog)

    def resolve_current_level(self, learner_id: uuid.UUID):
        state = self.progression.get_or_create_state(learner_id)
        if not state.onboarding_completed:
            raise OnboardingRequired
        try:
            return CurriculumLevel(state.current_level)
        except ValueError as exc:
            raise CurrentLevelInvalid from exc

    @staticmethod
    def resolve_target_difficulty(context, level):
        assessed = [item for item in context.recent_sessions
                    if item.level == level and item.outcome in {
                        EvidenceKind.POSITIVE, EvidenceKind.NEGATIVE, EvidenceKind.PARTIAL}]
        base = assessed[0].difficulty if assessed and assessed[0].difficulty is not None else 2
        if len(assessed) >= 2 and all(x.outcome == EvidenceKind.POSITIVE for x in assessed[:2]):
            base += 1
        elif len(assessed) >= 2 and all(x.outcome == EvidenceKind.NEGATIVE for x in assessed[:2]):
            base -= 1
        return max(1, min(5, base)), len(assessed)

    def select_next(self, learner_id: uuid.UUID):
        level = self.resolve_current_level(learner_id)
        context = AdaptiveContextBuilder().build(self.db, learner_id, self.catalog)
        target, history_count = self.resolve_target_difficulty(context, level)
        active = self.db.scalar(select(LearningSession).where(
            LearningSession.learner_id == learner_id,
            LearningSession.status == LearningSessionStatus.ACTIVE,
        ).order_by(LearningSession.updated_at.desc(), LearningSession.created_at.desc(), LearningSession.id.desc()))
        if active:
            problem = self.catalog.get_many((active.problem_id,), self.db).get(active.problem_id)
            if problem is None:
                raise GuidedProblemUnavailable
            return problem, level, target, "resume_active", None, history_count, 0, 0

        curriculum = self.catalog.curriculum_repository
        programme = curriculum.resolve_programme(level, self.catalog.academic_year)
        eligible = ProblemSelector(self.catalog.list_static(), curriculum, programme.id).compatible_candidates(level=level)
        if not eligible:
            raise GuidedProblemUnavailable
        solved = self.progression.solved_problem_ids(learner_id, level.value)
        unsolved = [problem for problem in eligible if problem.id not in solved]
        pool = unsolved or eligible
        result = AdaptiveSelectionService().select(pool, context, target)
        if result.problem is None:
            raise GuidedProblemUnavailable
        return (result.problem, level, target, "unsolved" if unsolved else "review",
                result.adaptation, history_count, len(eligible), len(unsolved))
