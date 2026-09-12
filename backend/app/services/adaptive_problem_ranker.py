"""Small, explainable scoring layer over hard-compatible corpus candidates."""
from dataclasses import dataclass
from enum import StrEnum

from app.domain.problem import Problem
from app.services.adaptive_context import AdaptiveContext
from app.services.knowledge_resolver import knowledge_for_problem

EXACT_DIFFICULTY_MATCH = 100
TARGET_KNOWLEDGE = 70
PREREQUISITE_REINFORCEMENT = 60
RECOMMENDED_AFTER = 30
RECENTLY_COMPLETED_SAME_PROBLEM = -200
RECENTLY_ABANDONED_SAME_PROBLEM = -120
VERY_RECENT_KNOWLEDGE_REPEAT = -25
VERY_RECENT_FAMILY_REPEAT = -350
DIFFICULTY_DISTANCE = -25
VERY_RECENT_LIMIT = 5


class AdaptationReasonCode(StrEnum):
    TARGET_KNOWLEDGE = "target_knowledge"
    PREREQUISITE_REINFORCEMENT = "prerequisite_reinforcement"
    KNOWLEDGE_DIVERSITY = "knowledge_diversity"
    RECOMMENDED_SEQUENCE = "recommended_sequence"
    RECENT_PROBLEM_AVOIDANCE = "recent_problem_avoidance"
    FAMILY_DIVERSITY = "family_diversity"
    APPROPRIATE_DIFFICULTY = "appropriate_difficulty"
    # Compatibility codes, no longer emitted by the canonical v2 flow.
    TARGET_TOPIC = "target_topic"
    TARGET_SKILL = "target_skill"
    TARGET_PREREQUISITE = "target_prerequisite"
    TOPIC_DIVERSITY = "topic_diversity"


@dataclass(frozen=True)
class AdaptiveCandidateScore:
    problem: Problem
    score: int
    reasons: tuple[AdaptationReasonCode, ...]


class AdaptiveProblemRanker:
    def rank(self, candidates: list[Problem], context: AdaptiveContext, requested_difficulty: int | None) -> list[AdaptiveCandidateScore]:
        recent = context.recent_sessions[:VERY_RECENT_LIMIT]
        completed_ids = {item.problem_id for item in context.recent_sessions if item.status.value == "completed"}
        ranked = [self._score(problem, context, recent, completed_ids, requested_difficulty) for problem in candidates]
        return sorted(ranked, key=lambda item: (-item.score, item.problem.id))

    def _score(self, problem, context, recent, completed_ids, requested_difficulty):
        score = 0; reasons = []
        knowledge_ids = set(knowledge_for_problem(problem, context.curriculum).knowledge_ids) if context.curriculum else set()
        if requested_difficulty is not None:
            distance = abs(problem.curriculum.difficulty - requested_difficulty)
            score += EXACT_DIFFICULTY_MATCH if distance == 0 else DIFFICULTY_DISTANCE * distance
            if distance == 0: reasons.append(AdaptationReasonCode.APPROPRIATE_DIFFICULTY)
        if knowledge_ids & set(context.target_knowledge_ids):
            score += TARGET_KNOWLEDGE; reasons.append(AdaptationReasonCode.TARGET_KNOWLEDGE)
        if knowledge_ids & set(context.prerequisite_knowledge_ids):
            score += PREREQUISITE_REINFORCEMENT; reasons.append(AdaptationReasonCode.PREREQUISITE_REINFORCEMENT)
        # Legacy contexts remain rankable during API transition.
        if not context.target_knowledge_ids and set(problem.prerequisites) & set(context.target_prerequisites):
            score += PREREQUISITE_REINFORCEMENT; reasons.append(AdaptationReasonCode.TARGET_PREREQUISITE)
        if not context.target_knowledge_ids and set(problem.skills) & set(context.target_skills):
            score += 50; reasons.append(AdaptationReasonCode.TARGET_SKILL)
        if not context.target_knowledge_ids and set(problem.topics) & set(context.target_topics):
            score += 40; reasons.append(AdaptationReasonCode.TARGET_TOPIC)
        if set(problem.recommended_after) & completed_ids:
            score += RECOMMENDED_AFTER; reasons.append(AdaptationReasonCode.RECOMMENDED_SEQUENCE)
        for learning in recent:
            if learning.problem_id == problem.id:
                score += RECENTLY_COMPLETED_SAME_PROBLEM if learning.status.value == "completed" else RECENTLY_ABANDONED_SAME_PROBLEM
                reasons.append(AdaptationReasonCode.RECENT_PROBLEM_AVOIDANCE)
            if knowledge_ids & set(learning.knowledge_ids): score += VERY_RECENT_KNOWLEDGE_REPEAT
            if problem.generation and learning.family_id and problem.generation.family_id == learning.family_id:
                score += VERY_RECENT_FAMILY_REPEAT
        if problem.generation and recent and not any(problem.generation.family_id == item.family_id for item in recent):
            reasons.append(AdaptationReasonCode.FAMILY_DIVERSITY)
        if knowledge_ids and recent and not any(knowledge_ids & set(item.knowledge_ids) for item in recent):
            reasons.append(AdaptationReasonCode.KNOWLEDGE_DIVERSITY)
        elif not context.curriculum and recent and not any(set(problem.topics) & set(x.topics) for x in recent):
            reasons.append(AdaptationReasonCode.TOPIC_DIVERSITY)
        return AdaptiveCandidateScore(problem, score, tuple(dict.fromkeys(reasons)))
