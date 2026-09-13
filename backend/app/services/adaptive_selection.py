"""Canonical adaptive ranking orchestration shared by legacy and guided APIs."""
from dataclasses import dataclass

from app.schemas.problem import ProblemSelectionAdaptation
from app.services.adaptive_problem_ranker import AdaptiveProblemRanker, AdaptationReasonCode


@dataclass(frozen=True)
class AdaptiveSelection:
    problem: object | None
    adaptation: ProblemSelectionAdaptation | None


class AdaptiveSelectionService:
    def select(self, candidates, context, target_difficulty) -> AdaptiveSelection:
        ranked = AdaptiveProblemRanker().rank(list(candidates), context, target_difficulty)
        if not ranked:
            return AdaptiveSelection(None, None)
        winner = ranked[0]
        reasons = [reason for reason in winner.reasons
                   if reason != AdaptationReasonCode.APPROPRIATE_DIFFICULTY]
        recent_ids = {item.problem_id for item in context.recent_sessions[:5]}
        if recent_ids and winner.problem.id not in recent_ids:
            reasons.append(AdaptationReasonCode.RECENT_PROBLEM_AVOIDANCE)
        reasons = list(dict.fromkeys(reasons))[:4]
        adaptation = ProblemSelectionAdaptation(
            reason_codes=tuple(reason.value for reason in reasons),
            targeted_topics=context.target_topics,
            targeted_skills=context.target_skills,
            targeted_prerequisites=context.target_prerequisites,
            target_knowledge_ids=context.target_knowledge_ids,
        ) if reasons or context.target_knowledge_ids else None
        return AdaptiveSelection(winner.problem, adaptation)
