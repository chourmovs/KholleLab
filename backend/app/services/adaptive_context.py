"""Bounded, learner-scoped knowledge evidence used by deterministic selection."""
from dataclasses import dataclass
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.problem import Skill, Topic
from app.models.attempt import Attempt
from app.models.evaluation import Evaluation
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.models.tutor_assessment import TutorAssessmentRecord
from app.schemas.profile import MasteryState
from app.services.knowledge_resolver import knowledge_for_problem
from app.services.learner_profile import ProfileEvidence, classify, mastery_state, prerequisite_is_established

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
    family_id: str | None = None
    knowledge_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdaptiveContext:
    learner_id: uuid.UUID
    recent_sessions: tuple[RecentLearning, ...] = ()
    # Deprecated compatibility targeting fields; canonical v2 uses KnowledgeNode IDs.
    target_topics: tuple[Topic, ...] = ()
    target_skills: tuple[Skill, ...] = ()
    target_prerequisites: tuple[str, ...] = ()
    target_knowledge_ids: tuple[str, ...] = ()
    prerequisite_knowledge_ids: tuple[str, ...] = ()
    curriculum: object | None = None


class AdaptiveContextBuilder:
    """Loads bounded evidence and resolves catalogue metadata in batched queries."""
    def build(self, db: Session, owner: uuid.UUID, catalog) -> AdaptiveContext:
        sessions = list(db.scalars(select(LearningSession).where(
            LearningSession.learner_id == owner,
            LearningSession.status.in_((LearningSessionStatus.COMPLETED, LearningSessionStatus.ABANDONED)),
        ).order_by(LearningSession.updated_at.desc(), LearningSession.id.desc()).limit(ADAPTIVE_HISTORY_LIMIT)))
        curriculum = catalog.curriculum_repository
        if not sessions:
            return AdaptiveContext(learner_id=owner, curriculum=curriculum)
        session_ids = [item.id for item in sessions]
        attempts = list(db.scalars(select(Attempt).where(Attempt.session_id.in_(session_ids)).order_by(Attempt.started_at)))
        counts = dict(db.execute(select(Attempt.session_id, func.count(Attempt.id)).where(Attempt.session_id.in_(session_ids)).group_by(Attempt.session_id)).all())
        by_session = {}
        for attempt in attempts: by_session.setdefault(attempt.session_id, []).append(attempt)
        attempt_ids = [x.id for x in attempts]
        evaluations = list(db.scalars(select(Evaluation).where(Evaluation.attempt_id.in_(attempt_ids)))) if attempt_ids else []
        eval_by_attempt = {x.attempt_id:x for x in evaluations}
        tutor_rows = db.execute(select(Attempt.session_id, TutorAssessmentRecord.intervention_needed,
            TutorAssessmentRecord.resource_need, TutorAssessmentRecord.created_at).join(
            TutorAssessmentRecord, TutorAssessmentRecord.attempt_id == Attempt.id).where(
            Attempt.session_id.in_(session_ids), TutorAssessmentRecord.provider != "fallback").order_by(
            TutorAssessmentRecord.created_at.desc())).all()
        latest_tutor = {}
        for session_id, intervention, need, _created in tutor_rows:
            latest_tutor.setdefault(session_id, (intervention, need))
        catalogue = catalog.get_many((item.problem_id for item in sessions), db)
        recent_list = []
        evidence_by_node = {}
        for item in sessions:
            problem = catalogue.get(item.problem_id)
            if not problem: continue
            snapshot = item.curriculum_snapshot or {}
            knowledge_ids = tuple(snapshot.get("knowledge_ids", ())) if item.curriculum_snapshot else knowledge_for_problem(problem, curriculum).knowledge_ids
            knowledge_ids = tuple(x for x in knowledge_ids if x in curriculum.knowledge_nodes and curriculum.knowledge_nodes[x].kind != "domain")
            attempts_for_session = by_session.get(item.id, [])
            evaluation = next((eval_by_attempt[a.id] for a in reversed(attempts_for_session) if a.id in eval_by_attempt), None)
            outcome = classify(item.status, evaluation)
            support = latest_tutor.get(item.id, (False, None))
            difficulty = snapshot.get("difficulty", problem.curriculum.difficulty)
            profile_evidence = ProfileEvidence(item.status, item.completed_at or item.updated_at, difficulty, (), (), outcome, (), knowledge_ids)
            for identifier in knowledge_ids: evidence_by_node.setdefault(identifier, []).append(profile_evidence)
            recent_list.append(RecentLearning(item.problem_id, item.status, counts.get(item.id, 0), support[0], support[1],
                problem.topics, problem.skills, problem.prerequisites, difficulty,
                problem.generation.family_id if problem.generation else None, knowledge_ids))
        targets = []
        for item in recent_list:
            genuine_support = item.intervention_needed or item.resource_need in {"course_gap", "method_gap"}
            for identifier in item.knowledge_ids:
                state = mastery_state(evidence_by_node[identifier])
                if (state in {MasteryState.EMERGING, MasteryState.PRACTICING} or genuine_support) and identifier not in targets:
                    targets.append(identifier)
        targets = targets[:TARGET_LIMIT]
        prerequisite_targets = []
        for identifier in targets:
            for prerequisite in curriculum.knowledge_nodes[identifier].prerequisites:
                observations = evidence_by_node.get(prerequisite, [])
                if not prerequisite_is_established(observations) and prerequisite not in prerequisite_targets:
                    prerequisite_targets.append(prerequisite)
        return AdaptiveContext(owner, tuple(recent_list), target_knowledge_ids=tuple(targets),
                               prerequisite_knowledge_ids=tuple(prerequisite_targets[:TARGET_LIMIT]), curriculum=curriculum)
