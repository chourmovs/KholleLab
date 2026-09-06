from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.domain.problem import CurriculumLevel, Topic
from app.api.attempts import session as db_session
from app.schemas.problem import (ProblemCatalogueItem, ProblemPublicDetail, ProblemSelectionAdaptation,
                                 ProblemSelectionResult, SelectionMode, to_public_problem_detail)
from app.services.adaptive_context import AdaptiveContextBuilder
from app.services.adaptive_problem_ranker import AdaptiveProblemRanker, AdaptationReasonCode
from app.services.learner_identity import learner_id
from app.services.problem_selector import ProblemSelector
from app.services.problem_repository import ProblemRepository
from app.services.resource_resolver import ResourceContext, ResourceResolver
from app.core.logging import component_logger

router = APIRouter(prefix="/problems", tags=["problems"])


def repository(request: Request) -> ProblemRepository:
    return request.app.state.problem_repository


@router.get("/{problem_id}/resources")
def resolve_problem_resources(problem_id: str, request: Request) -> dict:
    problem = repository(request).get(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    resolver: ResourceResolver = request.app.state.resource_resolver
    matches = resolver.resolve(ResourceContext(
        curriculum_level=problem.curriculum.level,
        topics=problem.topics,
        prerequisites=problem.prerequisites,
        skills=problem.skills,
        tags=problem.tags,
        problem_id=problem.id,
        explicit_resource_refs=problem.resource_refs,
    ))
    return {"problem_id": problem.id, "resources": [match.resource for match in matches]}


@router.get("", response_model=list[ProblemCatalogueItem], response_model_exclude_none=True)
def list_problems(request: Request) -> list[ProblemCatalogueItem]:
    return [ProblemCatalogueItem.model_validate(problem) for problem in repository(request).list()]


@router.get("/select", response_model=ProblemSelectionResult, response_model_exclude_none=True)
def select_problem(request: Request, level: CurriculumLevel, difficulty: int | None = None,
                   topic: list[Topic] | None = None, exclude: list[str] | None = None,
                   mode: SelectionMode = SelectionMode.MANUAL,
                   db: Session = Depends(db_session)) -> ProblemSelectionResult:
    if difficulty is not None and not 1 <= difficulty <= 5:
        raise HTTPException(status_code=422, detail="difficulty must be between 1 and 5")
    problems = repository(request).list()
    selector = ProblemSelector(problems)
    selected = None
    adaptation = None
    history_count = 0
    candidate_count = 0
    if mode == SelectionMode.ADAPTIVE:
        try:
            context = AdaptiveContextBuilder().build(db, learner_id(request), problems)
            candidates = selector.compatible_candidates(level=level, topics=topic)
            candidate_count = len(candidates)
            history_count = len(context.recent_sessions)
            ranked = AdaptiveProblemRanker().rank(candidates, context, difficulty)
            if ranked:
                winner = ranked[0]
                selected = winner.problem
                public_reasons = [reason for reason in winner.reasons
                                  if reason != AdaptationReasonCode.APPROPRIATE_DIFFICULTY]
                recent_ids = {item.problem_id for item in context.recent_sessions[:5]}
                if recent_ids and selected.id not in recent_ids:
                    public_reasons.append(AdaptationReasonCode.RECENT_PROBLEM_AVOIDANCE)
                public_reasons = list(dict.fromkeys(public_reasons))[:4]
                if public_reasons:
                    adaptation = ProblemSelectionAdaptation(
                        reason_codes=tuple(reason.value for reason in public_reasons),
                        targeted_topics=context.target_topics,
                        targeted_skills=context.target_skills,
                        targeted_prerequisites=context.target_prerequisites,
                    )
        except Exception:
            component_logger("application").warning(
                "adaptive_context_failed level={} difficulty={} topic={}; using deterministic fallback",
                level.value, difficulty, topic,
            )
    if selected is None:
        exclusions = (exclude or []) if mode == SelectionMode.MANUAL else []
        selected = selector.select(level=level, difficulty=difficulty, topics=topic,
                                   exclude_ids=exclusions)
    if selected is None:
        component_logger("application").warning(
            "problem_selection_empty level={} difficulty={} topic={} exclude_count={} corpus_count={} candidate_level_count={}",
            level.value, difficulty, topic[0].value if topic and len(topic) == 1 else topic,
            len(exclude or []), len(problems), sum(p.curriculum.level == level for p in problems),
        )
    actual = selected.curriculum.difficulty if selected else None
    detail = None if selected is None else to_public_problem_detail(selected)
    fallback_used = bool(selected and difficulty is not None and actual != difficulty)
    if mode == SelectionMode.ADAPTIVE:
        component_logger("application").info(
            "adaptive_problem_selected requested_level={} requested_difficulty={} requested_topic={} "
            "candidate_count={} history_count={} selected_problem_id={} selected_difficulty={} fallback_used={} reason_codes={}",
            level.value, difficulty, topic, candidate_count, history_count, selected.id if selected else None,
            actual, fallback_used, adaptation.reason_codes if adaptation else (),
        )
    return ProblemSelectionResult(problem=detail, requested_level=level, requested_difficulty=difficulty,
                                  actual_difficulty=actual, fallback_used=fallback_used,
                                  selection_mode=mode, adaptation=adaptation)


@router.get("/{problem_id}", response_model=ProblemPublicDetail, response_model_exclude_none=True)
def get_problem(problem_id: str, request: Request) -> ProblemPublicDetail:
    problem = repository(request).get(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return to_public_problem_detail(problem)
