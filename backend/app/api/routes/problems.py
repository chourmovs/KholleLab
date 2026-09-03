from fastapi import APIRouter, HTTPException

from app.schemas.problem import Problem

router = APIRouter(prefix="/problems", tags=["problems"])

DEMO_PROBLEM = Problem(
    id="demo-001",
    title="Échauffement algébrique",
    level="Première / Terminale",
    difficulty=2,
    topics=["algèbre", "raisonnement"],
    statement_tex=(
        r"\text{Déterminer tous les réels }x\text{ tels que }"
        r"\sqrt{x+2}+\sqrt{4-x}=3."
    ),
)


@router.get("/{problem_id}", response_model=Problem)
def get_problem(problem_id: str) -> Problem:
    if problem_id != DEMO_PROBLEM.id:
        raise HTTPException(status_code=404, detail="Problem not found")
    return DEMO_PROBLEM
