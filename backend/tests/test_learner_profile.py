from datetime import datetime, timezone

from app.models.evaluation import Evaluation, EvaluationStatus
from app.models.learning_session import LearningSessionStatus
from app.schemas.profile import MasteryState
from app.services.learner_profile import EvidenceKind, ProfileEvidence, classify, mastery_state


def evidence(kind: EvidenceKind, node="factorisation") -> ProfileEvidence:
    return ProfileEvidence(LearningSessionStatus.COMPLETED, datetime.now(timezone.utc), 2,
                           ("algebra",), ("reasoning",), kind, (), (node,))


def evaluation(status=EvaluationStatus.COMPLETED, verdict="correct", confidence=.9):
    return Evaluation(status=status, verdict=verdict, confidence=confidence, provider="fake",
                      model="fake", prompt_version="test", attempt_id=None)


def test_explicit_mastery_rules_use_assessed_evidence_only():
    positive=evidence(EvidenceKind.POSITIVE); partial=evidence(EvidenceKind.PARTIAL); negative=evidence(EvidenceKind.NEGATIVE)
    assert mastery_state([]) == MasteryState.NOT_ENOUGH_DATA
    assert mastery_state([positive]) == MasteryState.NOT_ENOUGH_DATA
    assert mastery_state([positive,negative]) == MasteryState.EMERGING
    assert mastery_state([partial,partial,positive]) == MasteryState.PRACTICING
    assert mastery_state([positive,positive,positive,partial]) == MasteryState.ESTABLISHED
    assert mastery_state([negative,negative,positive,positive,positive,positive]) != MasteryState.ESTABLISHED
    assert mastery_state([negative,positive,positive,positive,positive]) == MasteryState.ESTABLISHED
    assert mastery_state([evidence(EvidenceKind.UNASSESSED)] * 6) == MasteryState.NOT_ENOUGH_DATA


def test_evaluation_semantics_are_conservative_and_explicit():
    assert classify(LearningSessionStatus.COMPLETED,evaluation(confidence=.9)) == EvidenceKind.POSITIVE
    assert classify(LearningSessionStatus.COMPLETED,evaluation(confidence=.4)) == EvidenceKind.UNASSESSED
    assert classify(LearningSessionStatus.COMPLETED,evaluation(status=EvaluationStatus.FAILED)) == EvidenceKind.UNASSESSED
    assert classify(LearningSessionStatus.COMPLETED,None) == EvidenceKind.UNASSESSED
    assert classify(LearningSessionStatus.COMPLETED,evaluation(verdict="partial")) == EvidenceKind.PARTIAL
    assert classify(LearningSessionStatus.COMPLETED,evaluation(verdict="incorrect")) == EvidenceKind.NEGATIVE
    assert classify(LearningSessionStatus.COMPLETED,evaluation(verdict="non_answer")) == EvidenceKind.NEGATIVE
    assert classify(LearningSessionStatus.ABANDONED,evaluation()) == EvidenceKind.INCOMPLETE
