"""Small, explainable scoring layer over hard-compatible corpus candidates."""
from dataclasses import dataclass
from enum import StrEnum

from app.domain.problem import Problem
from app.services.adaptive_context import AdaptiveContext

EXACT_DIFFICULTY_MATCH = 100
TARGET_PREREQUISITE = 60
TARGET_SKILL = 50
TARGET_TOPIC = 40
RECOMMENDED_AFTER = 30
RECENTLY_COMPLETED_SAME_PROBLEM = -200
RECENTLY_ABANDONED_SAME_PROBLEM = -120
VERY_RECENT_TOPIC_REPEAT = -30
VERY_RECENT_SKILL_REPEAT = -15
DIFFICULTY_DISTANCE = -25
VERY_RECENT_LIMIT = 5


class AdaptationReasonCode(StrEnum):
    TARGET_TOPIC = "target_topic"
    TARGET_SKILL = "target_skill"
    TARGET_PREREQUISITE = "target_prerequisite"
    RECOMMENDED_SEQUENCE = "recommended_sequence"
    RECENT_PROBLEM_AVOIDANCE = "recent_problem_avoidance"
    TOPIC_DIVERSITY = "topic_diversity"
    APPROPRIATE_DIFFICULTY = "appropriate_difficulty"


@dataclass(frozen=True)
class AdaptiveCandidateScore:
    problem: Problem
    score: int
    reasons: tuple[AdaptationReasonCode, ...]


class AdaptiveProblemRanker:
    def rank(self, candidates: list[Problem], context: AdaptiveContext,
             requested_difficulty: int | None) -> list[AdaptiveCandidateScore]:
        recent = context.recent_sessions[:VERY_RECENT_LIMIT]
        completed_ids = {item.problem_id for item in context.recent_sessions if item.status.value == "completed"}
        ranked = [self._score(problem, context, recent, completed_ids, requested_difficulty)
                  for problem in candidates]
        return sorted(ranked, key=lambda item: (-item.score, item.problem.id))

    def _score(self, problem, context, recent, completed_ids, requested_difficulty):
        score = 0
        reasons = []
        if requested_difficulty is not None:
            distance = abs(problem.curriculum.difficulty - requested_difficulty)
            score += EXACT_DIFFICULTY_MATCH if distance == 0 else DIFFICULTY_DISTANCE * distance
            if distance == 0:
                reasons.append(AdaptationReasonCode.APPROPRIATE_DIFFICULTY)
        if set(problem.prerequisites) & set(context.target_prerequisites):
            score += TARGET_PREREQUISITE; reasons.append(AdaptationReasonCode.TARGET_PREREQUISITE)
        if set(problem.skills) & set(context.target_skills):
            score += TARGET_SKILL; reasons.append(AdaptationReasonCode.TARGET_SKILL)
        if set(problem.topics) & set(context.target_topics):
            score += TARGET_TOPIC; reasons.append(AdaptationReasonCode.TARGET_TOPIC)
        if set(problem.recommended_after) & completed_ids:
            score += RECOMMENDED_AFTER; reasons.append(AdaptationReasonCode.RECOMMENDED_SEQUENCE)
        for learning in recent:
            if learning.problem_id == problem.id:
                score += RECENTLY_COMPLETED_SAME_PROBLEM if learning.status.value == "completed" else RECENTLY_ABANDONED_SAME_PROBLEM
                reasons.append(AdaptationReasonCode.RECENT_PROBLEM_AVOIDANCE)
            if set(problem.topics) & set(learning.topics):
                score += VERY_RECENT_TOPIC_REPEAT
            if set(problem.skills) & set(learning.skills):
                score += VERY_RECENT_SKILL_REPEAT
        if recent and not any(set(problem.topics) & set(learning.topics) for learning in recent):
            reasons.append(AdaptationReasonCode.TOPIC_DIVERSITY)
        return AdaptiveCandidateScore(problem, score, tuple(dict.fromkeys(reasons)))
