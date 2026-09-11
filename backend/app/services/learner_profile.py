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
from app.schemas.profile import MasteryEvidenceSummary, MasteryState

PROFILE_EVIDENCE_SESSION_LIMIT = 50
PROFILE_RECENT_EVIDENCE_PER_ITEM = 6
PROFILE_MIN_EVALUATION_CONFIDENCE = 0.65
PROFILE_MIN_EVIDENCE = 2
PROFILE_PRACTICING_MIN_EVIDENCE = 3
PROFILE_ESTABLISHED_MIN_EVIDENCE = 4

LABELS = {"algebra":"Algèbre","analysis":"Analyse","arithmetic":"Arithmétique","combinatorics":"Combinatoire","geometry":"Géométrie","inequalities":"Inégalités","probability":"Probabilités","sequences":"Suites","functions":"Fonctions","complex-numbers":"Nombres complexes","logic":"Logique","equations":"Équations","trigonometry":"Trigonométrie","derivatives":"Dérivation","integrals":"Intégration","limits":"Limites","linear-algebra":"Algèbre linéaire","polynomials":"Polynômes","differential-equations":"Équations différentielles","calculation":"Calcul","proof":"Démonstration","reasoning":"Raisonnement","modeling":"Modélisation","sign-analysis":"Étude de signe","graph-reading":"Lecture graphique","equation-solving":"Résolution d’équations","inequality-solving":"Résolution d’inéquations","induction":"Récurrence","contradiction":"Raisonnement par l’absurde","case-analysis":"Étude de cas","construction":"Construction","estimation":"Estimation","optimization":"Optimisation"}

class EvidenceKind(StrEnum):
    STRONG_POSITIVE="strong_positive"
    WEAK_POSITIVE="weak_positive"
    NEUTRAL_PRACTICE="neutral_practice"
    NEGATIVE="negative"

@dataclass(frozen=True)
class ProfileEvidence:
    status: LearningSessionStatus
    timestamp: datetime
    difficulty: int
    topics: tuple[str, ...]
    skills: tuple[str, ...]
    outcome: EvidenceKind
    support: tuple[str, ...]

def classify(status: LearningSessionStatus, evaluation: Evaluation | None) -> EvidenceKind:
    if status == LearningSessionStatus.ABANDONED:
        return EvidenceKind.NEGATIVE
    if not evaluation or evaluation.status != EvaluationStatus.COMPLETED or evaluation.confidence is None or evaluation.confidence < PROFILE_MIN_EVALUATION_CONFIDENCE:
        return EvidenceKind.WEAK_POSITIVE
    verdict = (evaluation.verdict or "").lower()
    if verdict in {"correct", "mostly_correct"}: return EvidenceKind.STRONG_POSITIVE
    if verdict == "partial": return EvidenceKind.NEUTRAL_PRACTICE
    if verdict in {"incorrect", "non_answer"}: return EvidenceKind.NEGATIVE
    return EvidenceKind.WEAK_POSITIVE

def mastery_state(items: list[ProfileEvidence]) -> MasteryState:
    recent = items[:PROFILE_RECENT_EVIDENCE_PER_ITEM]
    if len(recent) < PROFILE_MIN_EVIDENCE: return MasteryState.NOT_ENOUGH_DATA
    positive = sum(x.outcome in {EvidenceKind.STRONG_POSITIVE,EvidenceKind.WEAK_POSITIVE,EvidenceKind.NEUTRAL_PRACTICE} for x in recent)
    strong = sum(x.outcome == EvidenceKind.STRONG_POSITIVE for x in recent)
    repeated_negative = len(recent)>=2 and all(x.outcome == EvidenceKind.NEGATIVE for x in recent[:2])
    if len(recent)>=PROFILE_ESTABLISHED_MIN_EVIDENCE and positive>=3 and strong>=2 and not repeated_negative:
        return MasteryState.ESTABLISHED
    if len(recent)>=PROFILE_PRACTICING_MIN_EVIDENCE and positive>=2 and not repeated_negative:
        return MasteryState.PRACTICING
    return MasteryState.EMERGING

class LearnerProfileBuilder:
    """Read-only, bounded synthesis. Seven bounded queries, independent of corpus/topic size."""
    def __init__(self, db: Session, repository): self.db=db; self.repository=repository

    def build(self, owner: uuid.UUID) -> dict:
        now=datetime.now(timezone.utc); terminal=(LearningSessionStatus.COMPLETED,LearningSessionStatus.ABANDONED)
        row=self.db.execute(select(func.count(LearningSession.id),func.sum(case((LearningSession.status==LearningSessionStatus.COMPLETED,1),else_=0)),func.sum(case((LearningSession.status==LearningSessionStatus.ABANDONED,1),else_=0)),func.sum(case((LearningSession.updated_at>=now-timedelta(days=7),1),else_=0)),func.sum(case((LearningSession.updated_at>=now-timedelta(days=30),1),else_=0)),func.sum(case(((LearningSession.status==LearningSessionStatus.COMPLETED)&(LearningSession.updated_at>=now-timedelta(days=30)),1),else_=0))).where(LearningSession.learner_id==owner)).one()
        sessions=list(self.db.scalars(select(LearningSession).where(LearningSession.learner_id==owner,LearningSession.status.in_(terminal)).order_by(LearningSession.updated_at.desc(),LearningSession.id.desc()).limit(PROFILE_EVIDENCE_SESSION_LIMIT)))
        session_ids=[s.id for s in sessions]
        attempts=list(self.db.scalars(select(Attempt).where(Attempt.session_id.in_(session_ids)))) if session_ids else []
        attempt_ids=[a.id for a in attempts]
        evaluations=list(self.db.scalars(select(Evaluation).where(Evaluation.attempt_id.in_(attempt_ids),Evaluation.status==EvaluationStatus.COMPLETED))) if attempt_ids else []
        tutors=list(self.db.scalars(select(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id.in_(attempt_ids)))) if attempt_ids else []
        attempts_total=self.db.scalar(select(func.count(Attempt.id)).join(LearningSession,Attempt.session_id==LearningSession.id).where(LearningSession.learner_id==owner)) or 0
        evaluations_total=self.db.scalar(select(func.count(Evaluation.id)).join(Attempt,Evaluation.attempt_id==Attempt.id).join(LearningSession,Attempt.session_id==LearningSession.id).where(LearningSession.learner_id==owner,Evaluation.status==EvaluationStatus.COMPLETED)) or 0
        by_session=defaultdict(list); eval_by_attempt={e.attempt_id:e for e in evaluations}; support_by_attempt=defaultdict(list)
        for a in attempts: by_session[a.session_id].append(a)
        for t in tutors:
            if t.provider == "fallback": continue
            if t.intervention_needed: support_by_attempt[t.attempt_id].append("repeated_support")
            if t.resource_need in {"course_gap","method_gap"}: support_by_attempt[t.attempt_id].append(t.resource_need)
        evidence=[]
        for s in sessions:
            problem=self.repository.get(s.problem_id)
            if not problem: continue
            session_attempts=by_session[s.id]; evaluation=next((eval_by_attempt[a.id] for a in reversed(session_attempts) if a.id in eval_by_attempt),None)
            support=tuple(sorted(set(x for a in session_attempts for x in support_by_attempt[a.id])))
            evidence.append(ProfileEvidence(s.status,s.completed_at or s.updated_at,problem.curriculum.difficulty,tuple(dict.fromkeys(x.value for x in problem.topics)),tuple(dict.fromkeys(x.value for x in problem.skills)),classify(s.status,evaluation),support))
        topics=self._aggregate(evidence,"topics"); skills=self._aggregate(evidence,"skills")
        candidates=[]
        for kind, item in [("topic",x) for x in topics]+[("skill",x) for x in skills]:
            reasons=[]
            if item.state in {MasteryState.EMERGING,MasteryState.PRACTICING}:
                if "course_gap" in item.support_signals: reasons.append("course_gap")
                if "method_gap" in item.support_signals: reasons.append("method_gap")
                if item.abandoned_sessions: reasons.append("recent_incomplete_work")
                if not reasons: reasons.append("inconsistent_results")
            if reasons: candidates.append((kind,item,reasons))
        candidates.sort(key=lambda x:(-len(x[2]),-x[1].last_practiced_at.timestamp(),-x[1].evidence_count,x[1].identifier))
        activity={"sessions_total":row[0] or 0,"sessions_completed":row[1] or 0,"sessions_abandoned":row[2] or 0,"attempts_total":attempts_total,"evaluations_completed":evaluations_total,"sessions_last_7_days":row[3] or 0,"sessions_last_30_days":row[4] or 0,"completed_last_30_days":row[5] or 0}
        return {"activity":activity,"topics":topics,"skills":skills,"strengths":[x for x in topics+skills if x.state==MasteryState.ESTABLISHED][:3],"needs_consolidation":[{"kind":k,"identifier":x.identifier,"label":x.label,"state":x.state,"reasons":r} for k,x,r in candidates[:3]],"generated_at":now,"evidence_window":{"sessions_considered":len(sessions),"max_sessions":PROFILE_EVIDENCE_SESSION_LIMIT}}

    def _aggregate(self,evidence:list[ProfileEvidence],field:str):
        grouped=defaultdict(list)
        for item in evidence:
            for identifier in getattr(item,field): grouped[identifier].append(item)
        result=[]
        for identifier,items in grouped.items():
            items.sort(key=lambda x:x.timestamp,reverse=True); difficulties=[x.difficulty for x in items]; positive=[x.difficulty for x in items if x.outcome in {EvidenceKind.STRONG_POSITIVE,EvidenceKind.WEAK_POSITIVE}]; signals=Counter(s for x in items[:PROFILE_RECENT_EVIDENCE_PER_ITEM] for s in x.support)
            result.append(MasteryEvidenceSummary(identifier=identifier,label=LABELS.get(identifier,identifier.replace("-"," ").capitalize()),state=mastery_state(items),evidence_count=len(items),completed_sessions=sum(x.status==LearningSessionStatus.COMPLETED for x in items),abandoned_sessions=sum(x.status==LearningSessionStatus.ABANDONED for x in items),recent_sessions=min(len(items),PROFILE_RECENT_EVIDENCE_PER_ITEM),difficulty_min=min(difficulties),difficulty_max=max(difficulties),highest_positive_difficulty=max(positive) if positive else None,last_practiced_at=items[0].timestamp,support_signals=sorted(k for k,v in signals.items() if v)))
        order={MasteryState.ESTABLISHED:0,MasteryState.PRACTICING:1,MasteryState.EMERGING:2,MasteryState.NOT_ENOUGH_DATA:3}
        return sorted(result,key=lambda x:(order[x.state],-x.last_practiced_at.timestamp(),x.identifier))
