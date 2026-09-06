from fastapi import APIRouter, HTTPException, Request

from app.domain.problem import CurriculumLevel, Topic
from app.schemas.problem import ProblemCatalogueItem, ProblemPublicDetail, ProblemSelectionResult, to_public_problem_detail
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
                   topic: list[Topic] | None = None, exclude: list[str] | None = None) -> ProblemSelectionResult:
    if difficulty is not None and not 1 <= difficulty <= 5:
        raise HTTPException(status_code=422, detail="difficulty must be between 1 and 5")
    problems = repository(request).list()
    selected = ProblemSelector(problems).select(
        level=level, difficulty=difficulty, topics=topic, exclude_ids=exclude or [])
    if selected is None:
        component_logger("application").warning(
            "problem_selection_empty level={} difficulty={} topic={} exclude_count={} corpus_count={} candidate_level_count={}",
            level.value, difficulty, topic[0].value if topic and len(topic) == 1 else topic,
            len(exclude or []), len(problems), sum(p.curriculum.level == level for p in problems),
        )
    actual = selected.curriculum.difficulty if selected else None
    detail = None if selected is None else to_public_problem_detail(selected)
    return ProblemSelectionResult(problem=detail, requested_level=level, requested_difficulty=difficulty,
                                  actual_difficulty=actual, fallback_used=bool(selected and difficulty is not None and actual != difficulty))


@router.get("/{problem_id}", response_model=ProblemPublicDetail, response_model_exclude_none=True)
def get_problem(problem_id: str, request: Request) -> ProblemPublicDetail:
    problem = repository(request).get(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return to_public_problem_detail(problem)
