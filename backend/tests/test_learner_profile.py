from datetime import datetime, timezone

from app.models.evaluation import Evaluation, EvaluationStatus
from app.models.learning_session import LearningSessionStatus
from app.schemas.profile import MasteryState
from app.services.learner_profile import EvidenceKind, ProfileEvidence, classify, mastery_state


def evidence(kind: EvidenceKind) -> ProfileEvidence:
    return ProfileEvidence(LearningSessionStatus.COMPLETED, datetime.now(timezone.utc), 2, ("algebra",), ("reasoning",), kind, ())


def evaluation(status=EvaluationStatus.COMPLETED, verdict="correct", confidence=.9):
    return Evaluation(status=status, verdict=verdict, confidence=confidence, provider="fake", model="fake", prompt_version="test", attempt_id=None)


def test_explicit_mastery_rules():
    strong=evidence(EvidenceKind.STRONG_POSITIVE); weak=evidence(EvidenceKind.WEAK_POSITIVE); negative=evidence(EvidenceKind.NEGATIVE)
    assert mastery_state([]) == MasteryState.NOT_ENOUGH_DATA
    assert mastery_state([strong]) == MasteryState.NOT_ENOUGH_DATA
    assert mastery_state([strong,negative]) == MasteryState.EMERGING
    assert mastery_state([weak,weak,weak]) == MasteryState.PRACTICING
    assert mastery_state([strong,strong,weak,weak]) == MasteryState.ESTABLISHED
    assert mastery_state([negative,negative,strong,strong,strong,strong]) != MasteryState.ESTABLISHED
    assert mastery_state([negative,strong,strong,strong,strong]) == MasteryState.ESTABLISHED


def test_evaluation_confidence_and_failure_are_conservative():
    assert classify(LearningSessionStatus.COMPLETED,evaluation(confidence=.9)) == EvidenceKind.STRONG_POSITIVE
    assert classify(LearningSessionStatus.COMPLETED,evaluation(confidence=.4)) == EvidenceKind.WEAK_POSITIVE
    assert classify(LearningSessionStatus.COMPLETED,evaluation(status=EvaluationStatus.FAILED)) == EvidenceKind.WEAK_POSITIVE
    assert classify(LearningSessionStatus.COMPLETED,None) == EvidenceKind.WEAK_POSITIVE
    assert classify(LearningSessionStatus.COMPLETED,evaluation(verdict="partial")) == EvidenceKind.NEUTRAL_PRACTICE
    assert classify(LearningSessionStatus.ABANDONED,evaluation()) == EvidenceKind.NEGATIVE
