from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import uuid

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.evaluation import Evaluation, EvaluationStatus
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.models.tutor_assessment import TutorAssessmentRecord
from app.schemas.profile import KnowledgeMasterySummary, MasteryEvidenceSummary, MasteryState
from app.services.knowledge_resolver import knowledge_for_problem

PROFILE_EVIDENCE_SESSION_LIMIT = 50
PROFILE_RECENT_EVIDENCE_PER_ITEM = 8
PROFILE_MIN_EVALUATION_CONFIDENCE = 0.65
PROFILE_MIN_EVIDENCE = 2
PROFILE_PRACTICING_MIN_EVIDENCE = 3
PROFILE_ESTABLISHED_MIN_EVIDENCE = 4

LABELS = {"algebra":"Algèbre","analysis":"Analyse","arithmetic":"Arithmétique","combinatorics":"Combinatoire","geometry":"Géométrie","inequalities":"Inégalités","probability":"Probabilités","sequences":"Suites","functions":"Fonctions","complex-numbers":"Nombres complexes","logic":"Logique","equations":"Équations","trigonometry":"Trigonométrie","derivatives":"Dérivation","integrals":"Intégration","limits":"Limites","linear-algebra":"Algèbre linéaire","polynomials":"Polynômes","differential-equations":"Équations différentielles","calculation":"Calcul","proof":"Démonstration","reasoning":"Raisonnement","modeling":"Modélisation","sign-analysis":"Étude de signe","graph-reading":"Lecture graphique","equation-solving":"Résolution d’équations","inequality-solving":"Résolution d’inéquations","induction":"Récurrence","contradiction":"Raisonnement par l’absurde","case-analysis":"Étude de cas","construction":"Construction","estimation":"Estimation","optimization":"Optimisation"}


class EvidenceKind(StrEnum):
    POSITIVE = "positive"
    PARTIAL = "partial"
    NEGATIVE = "negative"
    UNASSESSED = "unassessed"
    INCOMPLETE = "incomplete"
    # Compatibility names for callers from mastery v1.
    STRONG_POSITIVE = "positive"
    NEUTRAL_PRACTICE = "partial"
    WEAK_POSITIVE = "unassessed"


@dataclass(frozen=True)
class ProfileEvidence:
    status: LearningSessionStatus
    timestamp: datetime
    difficulty: int
    topics: tuple[str, ...]
    skills: tuple[str, ...]
    outcome: EvidenceKind
    support: tuple[str, ...]
    knowledge_ids: tuple[str, ...] = ()


def classify(status: LearningSessionStatus, evaluation: Evaluation | None) -> EvidenceKind:
    if status == LearningSessionStatus.ABANDONED:
        return EvidenceKind.INCOMPLETE
    if (not evaluation or evaluation.status != EvaluationStatus.COMPLETED
            or evaluation.confidence is None
            or evaluation.confidence < PROFILE_MIN_EVALUATION_CONFIDENCE):
        return EvidenceKind.UNASSESSED
    verdict = (evaluation.verdict or "").lower()
    if verdict in {"correct", "mostly_correct"}:
        return EvidenceKind.POSITIVE
    if verdict == "partial":
        return EvidenceKind.PARTIAL
    if verdict in {"incorrect", "non_answer"}:
        return EvidenceKind.NEGATIVE
    return EvidenceKind.UNASSESSED


def mastery_state(items: list[ProfileEvidence]) -> MasteryState:
    assessed = [x for x in items if x.outcome in {EvidenceKind.POSITIVE, EvidenceKind.PARTIAL, EvidenceKind.NEGATIVE}]
    recent = assessed[:PROFILE_RECENT_EVIDENCE_PER_ITEM]
    if len(recent) < PROFILE_MIN_EVIDENCE:
        return MasteryState.NOT_ENOUGH_DATA
    positive = sum(x.outcome == EvidenceKind.POSITIVE for x in recent)
    useful = sum(x.outcome in {EvidenceKind.POSITIVE, EvidenceKind.PARTIAL} for x in recent)
    repeated_negative = len(recent) >= 2 and all(x.outcome == EvidenceKind.NEGATIVE for x in recent[:2])
    latest_three_positive = sum(x.outcome == EvidenceKind.POSITIVE for x in recent[:3])
    if (len(recent) >= PROFILE_ESTABLISHED_MIN_EVIDENCE and positive >= 3
            and latest_three_positive >= 2 and not repeated_negative):
        return MasteryState.ESTABLISHED
    if len(recent) >= PROFILE_PRACTICING_MIN_EVIDENCE and useful >= 2 and not repeated_negative:
        return MasteryState.PRACTICING
    return MasteryState.EMERGING


class LearnerProfileBuilder:
    """Read-only synthesis with seven bounded queries, independent of graph size."""
    def __init__(self, db: Session, repository):
        self.db = db
        self.repository = repository
        self.curriculum = repository.curriculum_repository

    def build(self, owner: uuid.UUID) -> dict:
        now = datetime.now(timezone.utc)
        terminal = (LearningSessionStatus.COMPLETED, LearningSessionStatus.ABANDONED)
        row = self.db.execute(select(func.count(LearningSession.id), func.sum(case((LearningSession.status == LearningSessionStatus.COMPLETED, 1), else_=0)), func.sum(case((LearningSession.status == LearningSessionStatus.ABANDONED, 1), else_=0)), func.sum(case((LearningSession.updated_at >= now-timedelta(days=7), 1), else_=0)), func.sum(case((LearningSession.updated_at >= now-timedelta(days=30), 1), else_=0)), func.sum(case(((LearningSession.status == LearningSessionStatus.COMPLETED) & (LearningSession.updated_at >= now-timedelta(days=30)), 1), else_=0))).where(LearningSession.learner_id == owner)).one()
        sessions = list(self.db.scalars(select(LearningSession).where(LearningSession.learner_id == owner, LearningSession.status.in_(terminal)).order_by(LearningSession.updated_at.desc(), LearningSession.id.desc()).limit(PROFILE_EVIDENCE_SESSION_LIMIT)))
        session_ids = [s.id for s in sessions]
        attempts = list(self.db.scalars(select(Attempt).where(Attempt.session_id.in_(session_ids)).order_by(Attempt.started_at))) if session_ids else []
        attempt_ids = [a.id for a in attempts]
        evaluations = list(self.db.scalars(select(Evaluation).where(Evaluation.attempt_id.in_(attempt_ids)))) if attempt_ids else []
        tutors = list(self.db.scalars(select(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id.in_(attempt_ids)))) if attempt_ids else []
        problems = self.repository.get_many((s.problem_id for s in sessions), self.db)
        attempts_total = self.db.scalar(select(func.count(Attempt.id)).join(LearningSession, Attempt.session_id == LearningSession.id).where(LearningSession.learner_id == owner)) or 0
        evaluations_total = self.db.scalar(select(func.count(Evaluation.id)).join(Attempt, Evaluation.attempt_id == Attempt.id).join(LearningSession, Attempt.session_id == LearningSession.id).where(LearningSession.learner_id == owner, Evaluation.status == EvaluationStatus.COMPLETED)) or 0
        by_session = defaultdict(list); eval_by_attempt = {e.attempt_id:e for e in evaluations}; support_by_attempt = defaultdict(list)
        for attempt in attempts:
            by_session[attempt.session_id].append(attempt)
        for tutor in tutors:
            if tutor.provider == "fallback":
                continue
            if tutor.intervention_needed:
                support_by_attempt[tutor.attempt_id].append("intervention_needed")
            if tutor.resource_need in {"course_gap", "method_gap"}:
                support_by_attempt[tutor.attempt_id].append(tutor.resource_need)
        evidence = []
        for session in sessions:
            problem = problems.get(session.problem_id)
            if not problem:
                continue
            session_attempts = by_session[session.id]
            evaluation = next((eval_by_attempt[a.id] for a in reversed(session_attempts) if a.id in eval_by_attempt), None)
            support = tuple(sorted(set(x for a in session_attempts for x in support_by_attempt[a.id])))
            snapshot = session.curriculum_snapshot or {}
            mapping = knowledge_for_problem(problem, self.curriculum)
            knowledge_ids = tuple(snapshot.get("knowledge_ids", ())) if session.curriculum_snapshot else mapping.knowledge_ids
            knowledge_ids = tuple(x for x in knowledge_ids if x in self.curriculum.knowledge_nodes and self.curriculum.knowledge_nodes[x].kind != "domain")
            difficulty = snapshot.get("difficulty", problem.curriculum.difficulty)
            evidence.append(ProfileEvidence(session.status, session.completed_at or session.updated_at, difficulty,
                tuple(dict.fromkeys(x.value for x in problem.topics)), tuple(dict.fromkeys(x.value for x in problem.skills)),
                classify(session.status, evaluation), support, knowledge_ids))
        knowledge = self._aggregate_knowledge(evidence)
        topics = self._aggregate_legacy(evidence, "topics")
        skills = self._aggregate_legacy(evidence, "skills")
        by_id = {item.identifier:item for item in knowledge}
        candidates = []
        for item in knowledge:
            reasons = []
            recent = [x for x in evidence if item.identifier in x.knowledge_ids][:PROFILE_RECENT_EVIDENCE_PER_ITEM]
            if sum(x.outcome == EvidenceKind.NEGATIVE for x in recent[:3]) >= 2: reasons.append("repeated_negative")
            if any(x.outcome == EvidenceKind.PARTIAL for x in recent): reasons.append("partial_results")
            for signal in ("course_gap", "method_gap"):
                if signal in item.support_signals: reasons.append(signal)
            if item.incomplete_sessions: reasons.append("incomplete_work")
            node = self.curriculum.knowledge_nodes[item.identifier]
            gaps = [p for p in node.prerequisites if p in by_id and by_id[p].state != MasteryState.ESTABLISHED]
            if gaps: reasons.append("prerequisite_gap")
            if item.state in {MasteryState.EMERGING, MasteryState.PRACTICING} and not reasons: reasons.append("inconsistent_results")
            if reasons: candidates.append((item, reasons, gaps[:2]))
        candidates.sort(key=lambda x:(-len(x[1]), -x[0].last_practiced_at.timestamp(), x[0].identifier))
        consolidation = [{"kind":"knowledge", "identifier":item.identifier, "label":item.label,
                          "state":item.state, "reasons":reasons,
                          "prerequisites":[{"identifier":p,"label":self.curriculum.knowledge_nodes[p].label} for p in gaps]}
                         for item,reasons,gaps in candidates[:3]]
        activity = {"sessions_total":row[0] or 0,"sessions_completed":row[1] or 0,"sessions_abandoned":row[2] or 0,"attempts_total":attempts_total,"evaluations_completed":evaluations_total,"sessions_last_7_days":row[3] or 0,"sessions_last_30_days":row[4] or 0,"completed_last_30_days":row[5] or 0}
        return {"activity":activity,"topics":topics,"skills":skills,"knowledge":knowledge,
                "strengths":[x for x in knowledge if x.state == MasteryState.ESTABLISHED][:3],
                "needs_consolidation":consolidation,"generated_at":now,
                "evidence_window":{"sessions_considered":len(sessions),"max_sessions":PROFILE_EVIDENCE_SESSION_LIMIT}}

    def _aggregate_knowledge(self, evidence):
        grouped = defaultdict(list)
        for item in evidence:
            for identifier in item.knowledge_ids: grouped[identifier].append(item)
        result = []
        for identifier, items in grouped.items():
            node = self.curriculum.knowledge_nodes[identifier]
            result.append(self._summary(items, identifier, node.label, node))
        return self._sort(result)

    def _aggregate_legacy(self, evidence, field):
        grouped = defaultdict(list)
        for item in evidence:
            for identifier in getattr(item, field): grouped[identifier].append(item)
        return self._sort([self._summary(items, identifier, LABELS.get(identifier, identifier.replace("-", " ").capitalize())) for identifier,items in grouped.items()])

    def _summary(self, items, identifier, label, node=None):
        items.sort(key=lambda x:x.timestamp, reverse=True)
        recent = items[:PROFILE_RECENT_EVIDENCE_PER_ITEM]
        assessed = [x for x in recent if x.outcome in {EvidenceKind.POSITIVE,EvidenceKind.PARTIAL,EvidenceKind.NEGATIVE}]
        difficulties = [x.difficulty for x in items]
        positive_difficulties = [x.difficulty for x in items if x.outcome == EvidenceKind.POSITIVE]
        common = dict(identifier=identifier,label=label,state=mastery_state(items),evidence_count=len(items),
            difficulty_min=min(difficulties),difficulty_max=max(difficulties),highest_positive_difficulty=max(positive_difficulties) if positive_difficulties else None,
            last_practiced_at=items[0].timestamp,support_signals=sorted(Counter(s for x in recent for s in x.support)))
        if node:
            parent = self.curriculum.knowledge_nodes.get(node.parent) if node.parent else None
            return KnowledgeMasterySummary(**common,kind=node.kind,parent=node.parent,parent_label=parent.label if parent else None,
                assessed_evidence_count=len(assessed),positive_count=sum(x.outcome==EvidenceKind.POSITIVE for x in recent),
                partial_count=sum(x.outcome==EvidenceKind.PARTIAL for x in recent),negative_count=sum(x.outcome==EvidenceKind.NEGATIVE for x in recent),
                incomplete_sessions=sum(x.outcome==EvidenceKind.INCOMPLETE for x in recent),unassessed_sessions=sum(x.outcome==EvidenceKind.UNASSESSED for x in recent))
        return MasteryEvidenceSummary(**common,completed_sessions=sum(x.status==LearningSessionStatus.COMPLETED for x in items),
            abandoned_sessions=sum(x.status==LearningSessionStatus.ABANDONED for x in items),recent_sessions=len(recent))

    @staticmethod
    def _sort(result):
        order={MasteryState.ESTABLISHED:0,MasteryState.PRACTICING:1,MasteryState.EMERGING:2,MasteryState.NOT_ENOUGH_DATA:3}
        return sorted(result,key=lambda x:(order[x.state],-x.last_practiced_at.timestamp(),x.identifier))
