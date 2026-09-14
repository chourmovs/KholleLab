from enum import StrEnum

from app.models.evaluation import Evaluation, EvaluationStatus
from app.models.learning_session import LearningSessionStatus


MASTERY_MIN_EVALUATION_CONFIDENCE = 0.65


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


def classify_evidence(status: LearningSessionStatus, evaluation: Evaluation | None) -> EvidenceKind:
    """Canonical pedagogical classification shared by mastery and progression."""
    if status == LearningSessionStatus.ABANDONED:
        return EvidenceKind.INCOMPLETE
    if (status != LearningSessionStatus.COMPLETED
            or not evaluation
            or evaluation.status != EvaluationStatus.COMPLETED
            or evaluation.confidence is None
            or evaluation.confidence < MASTERY_MIN_EVALUATION_CONFIDENCE):
        return EvidenceKind.UNASSESSED
    verdict = (evaluation.verdict or "").lower()
    if verdict in {"correct", "mostly_correct"}:
        return EvidenceKind.POSITIVE
    if verdict == "partial":
        return EvidenceKind.PARTIAL
    if verdict in {"incorrect", "non_answer"}:
        return EvidenceKind.NEGATIVE
    return EvidenceKind.UNASSESSED


# Temporary import compatibility for mastery callers; new code uses the explicit name.
classify = classify_evidence
