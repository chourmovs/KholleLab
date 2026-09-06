"""Bounded, learner-scoped history used by deterministic selection."""
from dataclasses import dataclass
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.problem import Problem, Skill, Topic
from app.models.attempt import Attempt
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.models.tutor_assessment import TutorAssessmentRecord

ADAPTIVE_HISTORY_LIMIT = 20
TARGET_LIMIT = 3


@dataclass(frozen=True)
class RecentLearning:
    problem_id: str
    status: LearningSessionStatus
    attempt_count: int
    intervention_needed: bool
    resource_need: str | None
    topics: tuple[Topic, ...] = ()
    skills: tuple[Skill, ...] = ()
    prerequisites: tuple[str, ...] = ()
    difficulty: int | None = None


@dataclass(frozen=True)
class AdaptiveContext:
    learner_id: uuid.UUID
    recent_sessions: tuple[RecentLearning, ...] = ()
    target_topics: tuple[Topic, ...] = ()
    target_skills: tuple[Skill, ...] = ()
    target_prerequisites: tuple[str, ...] = ()


class AdaptiveContextBuilder:
    """Loads a bounded window with three queries, never one query per problem."""

    def build(self, db: Session, owner: uuid.UUID, problems: list[Problem]) -> AdaptiveContext:
        sessions = list(db.scalars(
            select(LearningSession).where(
                LearningSession.learner_id == owner,
                LearningSession.status.in_((LearningSessionStatus.COMPLETED, LearningSessionStatus.ABANDONED)),
            ).order_by(LearningSession.updated_at.desc(), LearningSession.id.desc()).limit(ADAPTIVE_HISTORY_LIMIT)
        ))
        if not sessions:
            return AdaptiveContext(learner_id=owner)
        session_ids = [item.id for item in sessions]
        counts = dict(db.execute(
            select(Attempt.session_id, func.count(Attempt.id)).where(Attempt.session_id.in_(session_ids)).group_by(Attempt.session_id)
        ).all())
        tutor_rows = db.execute(
            select(Attempt.session_id, TutorAssessmentRecord.intervention_needed,
                   TutorAssessmentRecord.resource_need, TutorAssessmentRecord.created_at)
            .join(TutorAssessmentRecord, TutorAssessmentRecord.attempt_id == Attempt.id)
            .where(Attempt.session_id.in_(session_ids))
            .order_by(TutorAssessmentRecord.created_at.desc())
        ).all()
        latest_tutor = {}
        for session_id, intervention, need, _created in tutor_rows:
            latest_tutor.setdefault(session_id, (intervention, need))
        catalogue = {problem.id: problem for problem in problems}
        recent = tuple(RecentLearning(
            problem_id=item.problem_id, status=item.status, attempt_count=counts.get(item.id, 0),
            intervention_needed=latest_tutor.get(item.id, (False, None))[0],
            resource_need=latest_tutor.get(item.id, (False, None))[1],
            topics=catalogue[item.problem_id].topics if item.problem_id in catalogue else (),
            skills=catalogue[item.problem_id].skills if item.problem_id in catalogue else (),
            prerequisites=catalogue[item.problem_id].prerequisites if item.problem_id in catalogue else (),
            difficulty=catalogue[item.problem_id].curriculum.difficulty if item.problem_id in catalogue else None,
        ) for item in sessions)
        meaningful = [item for item in recent if item.intervention_needed or item.resource_need in {"course_gap", "method_gap", "example_helpful"}]
        topics: list[Topic] = []
        skills: list[Skill] = []
        prerequisites: list[str] = []
        for item in meaningful:
            problem = catalogue.get(item.problem_id)
            if not problem:
                continue
            self._extend_unique(topics, problem.topics, TARGET_LIMIT)
            self._extend_unique(skills, problem.skills, TARGET_LIMIT)
            self._extend_unique(prerequisites, problem.prerequisites, TARGET_LIMIT)
        return AdaptiveContext(owner, recent, tuple(topics), tuple(skills), tuple(prerequisites))

    @staticmethod
    def _extend_unique(target: list, values, limit: int) -> None:
        for value in values:
            if value not in target and len(target) < limit:
                target.append(value)
