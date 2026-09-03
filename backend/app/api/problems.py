from fastapi import APIRouter, HTTPException, Request

from app.schemas.problem import ProblemCatalogueItem, ProblemPublicDetail
from app.services.problem_repository import ProblemRepository

router = APIRouter(prefix="/problems", tags=["problems"])


def repository(request: Request) -> ProblemRepository:
    return request.app.state.problem_repository


@router.get("", response_model=list[ProblemCatalogueItem], response_model_exclude_none=True)
def list_problems(request: Request) -> list[ProblemCatalogueItem]:
    return [ProblemCatalogueItem.model_validate(problem) for problem in repository(request).list()]


@router.get("/{problem_id}", response_model=ProblemPublicDetail, response_model_exclude_none=True)
def get_problem(problem_id: str, request: Request) -> ProblemPublicDetail:
    problem = repository(request).get(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return ProblemPublicDetail.model_validate(
        {**problem.model_dump(), "hint_levels": tuple(hint.level for hint in problem.hints)}
    )
