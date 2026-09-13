from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.evaluation import Evaluation, EvaluationStatus
from app.models.learning_session import LearningSessionStatus
from app.schemas.profile import MasteryState
from app.services.learner_profile import (
    EvidenceKind, LearnerProfileBuilder, ProfileEvidence, classify, mastery_state,
    prerequisite_is_established,
)


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


def test_prerequisite_requires_established_mastery_including_when_unseen():
    assert not prerequisite_is_established([])
    assert not prerequisite_is_established([evidence(EvidenceKind.UNASSESSED)])
    assert not prerequisite_is_established([evidence(EvidenceKind.PARTIAL)] * 3)
    assert prerequisite_is_established([evidence(EvidenceKind.POSITIVE)] * 4)


def test_knowledge_counters_separate_assessed_mastery_and_activity_windows():
    builder = LearnerProfileBuilder.__new__(LearnerProfileBuilder)
    builder.curriculum = SimpleNamespace(knowledge_nodes={})
    outcomes = [
        EvidenceKind.POSITIVE, EvidenceKind.UNASSESSED, EvidenceKind.INCOMPLETE,
        EvidenceKind.POSITIVE, EvidenceKind.PARTIAL, EvidenceKind.UNASSESSED,
    ]
    summary = builder._summary([evidence(kind) for kind in outcomes], "factorisation", "Factorisation",
                               SimpleNamespace(kind="procedure", parent=None))
    assert summary.assessed_evidence_count == 3
    assert (summary.positive_count, summary.partial_count, summary.negative_count) == (2, 1, 0)
    assert (summary.incomplete_sessions, summary.unassessed_sessions) == (1, 2)


def test_assessed_counter_window_skips_unassessed_activity():
    builder = LearnerProfileBuilder.__new__(LearnerProfileBuilder)
    builder.curriculum = SimpleNamespace(knowledge_nodes={})
    items = [evidence(EvidenceKind.UNASSESSED) for _ in range(8)] + [evidence(EvidenceKind.POSITIVE) for _ in range(4)]
    for index, item in enumerate(items):
        object.__setattr__(item, "timestamp", item.timestamp.replace(microsecond=100-index))
    summary = builder._summary(items, "factorisation", "Factorisation",
                               SimpleNamespace(kind="procedure", parent=None))
    assert summary.assessed_evidence_count == summary.positive_count == 4
    assert summary.unassessed_sessions == 8


def test_unseen_immediate_prerequisite_is_a_gap_without_fake_evidence():
    builder = LearnerProfileBuilder.__new__(LearnerProfileBuilder)
    prerequisite = SimpleNamespace(label="Développement algébrique")
    target = SimpleNamespace(kind="procedure", parent=None, prerequisites=("algebraic-expansion",))
    builder.curriculum = SimpleNamespace(knowledge_nodes={
        "factorisation": target, "algebraic-expansion": prerequisite,
    })
    observations = [evidence(EvidenceKind.PARTIAL)] * 3
    summary = builder._summary(observations, "factorisation", "Factorisation", target)
    consolidation = builder._consolidation(observations, [summary])
    assert [item.identifier for item in [summary]] == ["factorisation"]
    assert consolidation[0]["reasons"][:2] == ["partial_results", "prerequisite_gap"]
    assert consolidation[0]["prerequisites"] == [{
        "identifier":"algebraic-expansion", "label":"Développement algébrique", "status":"not_practiced"
    }]


def test_abandonment_alone_does_not_contradict_an_established_strength():
    builder = LearnerProfileBuilder.__new__(LearnerProfileBuilder)
    node = SimpleNamespace(kind="procedure", parent=None, prerequisites=())
    builder.curriculum = SimpleNamespace(knowledge_nodes={"linear-system":node})
    observations = [evidence(EvidenceKind.INCOMPLETE, "linear-system")] + [
        evidence(EvidenceKind.POSITIVE, "linear-system") for _ in range(4)
    ]
    summary = builder._summary(observations, "linear-system", "Systèmes linéaires", node)
    assert summary.state == MasteryState.ESTABLISHED
    assert summary.incomplete_sessions == 1
    assert builder._consolidation(observations, [summary]) == []


def test_established_mastery_is_never_also_a_consolidation_target():
    builder = LearnerProfileBuilder.__new__(LearnerProfileBuilder)
    prerequisite = SimpleNamespace(label="Prérequis")
    node = SimpleNamespace(kind="procedure", parent=None, prerequisites=("prerequisite",))
    builder.curriculum = SimpleNamespace(knowledge_nodes={"target": node, "prerequisite": prerequisite})
    observations = [evidence(EvidenceKind.PARTIAL, "target")] + [
        evidence(EvidenceKind.POSITIVE, "target") for _ in range(4)
    ]
    summary = builder._summary(observations, "target", "Cible", node)
    strengths = [summary] if summary.state == MasteryState.ESTABLISHED else []
    consolidation = builder._consolidation(observations, [summary])
    assert {item.identifier for item in strengths}.isdisjoint({item["identifier"] for item in consolidation})
