import uuid

from app.domain.problem import Problem
from app.models.learning_session import LearningSessionStatus
from app.services.adaptive_context import AdaptiveContext, RecentLearning
from app.services.adaptive_problem_ranker import AdaptiveProblemRanker, AdaptationReasonCode
from app.services.problem_selector import ProblemSelector


def problem(identifier, *, level="terminale", difficulty=3, topic="analysis",
            skills=(), prerequisites=(), recommended_after=(), family=None):
    raw = {
        "id": identifier, "title": identifier, "statement": "Test",
        "curriculum": {"level": level, "difficulty": difficulty}, "topics": [topic],
        "skills": skills, "prerequisites": prerequisites, "recommended_after": recommended_after,
        "source": {"type": "internal", "name": "Tests"}, "reference_solution": "Privée"}
    if family:
        raw["generation"] = {"kind": "parametric", "family_id": family, "version": 1,
                             "variant": 1, "parameter_identity": "a" * 64}
    return Problem.model_validate(raw)


def context(*recent, topics=(), skills=(), prerequisites=()):
    return AdaptiveContext(uuid.uuid4(), tuple(recent), tuple(topics), tuple(skills), tuple(prerequisites))


def learning(item, status=LearningSessionStatus.COMPLETED):
    return RecentLearning(item.id, status, 1, False, None, item.topics, item.skills,
                          item.prerequisites, item.curriculum.difficulty,
                          item.generation.family_id if item.generation else None)


def select(items, history, difficulty=3, topic=None):
    candidates = ProblemSelector(items).compatible_candidates(
        level="terminale", topics=[topic] if topic else None)
    return AdaptiveProblemRanker().rank(candidates, history, difficulty)[0]


def test_empty_history_and_ties_are_deterministic():
    items = [problem("problem-b"), problem("problem-a")]
    results = [select(items, context()).problem.id for _ in range(10)]
    assert results == ["problem-a"] * 10


def test_hard_level_and_topic_constraints_are_never_bypassed():
    items = [problem("geometry-ok", topic="geometry"),
             problem("wrong-topic", topic="analysis"),
             problem("wrong-level", level="maths-spe", topic="geometry")]
    candidates = ProblemSelector(items).compatible_candidates(level="terminale", topics=["geometry"])
    assert [item.id for item in candidates] == ["geometry-ok"]


def test_completed_and_abandoned_problem_retries_are_deprioritized_but_not_banned():
    used = problem("problem-used")
    alternative = problem("problem-new", topic="geometry")
    assert select([used, alternative], context(learning(used))).problem == alternative
    abandoned = learning(used, LearningSessionStatus.ABANDONED)
    assert select([used, alternative], context(abandoned)).problem == alternative
    assert select([used], context(learning(used))).problem == used


def test_tutor_targets_and_recommended_sequence_raise_relevant_candidates():
    previous = problem("problem-previous")
    target = problem("problem-target", skills=("induction",), prerequisites=("recurrence",),
                     recommended_after=(previous.id,))
    neutral = problem("problem-neutral")
    result = select([target, neutral], context(learning(previous), skills=("induction",),
                                                   prerequisites=("recurrence",)))
    assert result.problem == target
    assert {AdaptationReasonCode.TARGET_SKILL, AdaptationReasonCode.TARGET_PREREQUISITE,
            AdaptationReasonCode.RECOMMENDED_SEQUENCE} <= set(result.reasons)


def test_recent_topic_repetition_modestly_favours_diversity():
    previous = problem("problem-previous", topic="analysis")
    repeated = problem("problem-repeated", topic="analysis")
    diverse = problem("problem-diverse", topic="geometry")
    result = select([repeated, diverse], context(learning(previous)))
    assert result.problem == diverse
    assert AdaptationReasonCode.TOPIC_DIVERSITY in result.reasons


def test_requested_difficulty_remains_the_dominant_preference():
    exact = problem("problem-exact", difficulty=3, topic="analysis")
    easier = problem("problem-easier", difficulty=2, topic="geometry")
    assert select([exact, easier], context(), difficulty=3).problem == exact


def test_recent_family_is_strongly_avoided_but_never_creates_a_dead_end():
    used = problem("family-a-used", family="family-a")
    another_a = problem("family-a-new", family="family-a")
    family_b = problem("family-b-only", family="family-b")
    result = select([another_a, family_b], context(learning(used)))
    assert result.problem == family_b
    assert AdaptationReasonCode.FAMILY_DIVERSITY in result.reasons
    assert select([another_a], context(learning(used))).problem == another_a
