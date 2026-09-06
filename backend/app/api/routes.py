from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.version import APP_NAME, APP_VERSION
from app.api.problems import router as problems_router
from app.api.resources import router as resources_router
from app.api.attempts import router as attempts_router
from app.api.evaluations import router as evaluations_router
from app.core.config import settings
from app.services import health
from app.api.diagnostics import router as diagnostics_router
from app.domain.problem import CURRICULUM_ORDER
from app.services.inference_diagnostics import cached_status, diagnose
from app.schemas.evaluation import HealthResponse, InferenceStatusResponse
from app.core.logging import component_logger

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request):
    if not health.database_is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "service": "khollelab-api", "database": "unavailable"},
        )
    repository = request.app.state.problem_repository
    resource_repository = request.app.state.resource_repository
    if repository.count == 0 or resource_repository.count == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "service": "khollelab-api", "problem_count": repository.count,
                    "resource_count": resource_repository.count},
        )
    try:
        inference = cached_status()
    except Exception:
        component_logger("application").exception("Inference diagnostic failed during health check")
        inference = "error"
    return {"status": "ok", "service": "khollelab-api", "database": "ok", "problem_corpus": "ok", "problem_count": repository.count, "resource_corpus": "ok", "resource_count": resource_repository.count, "curriculum_levels": len({p.curriculum.level for p in repository.list()}), "inference": inference}

@router.get("/inference/status", response_model=InferenceStatusResponse)
async def get_inference_status(refresh: bool = Query(False)):
    result = await diagnose(force=refresh)
    return {key:value for key,value in result.items() if key != "checks"}


@router.get("/curriculum")
def get_curriculum() -> dict:
    labels = {"seconde":"Seconde", "premiere":"Première", "terminale":"Terminale", "maths-sup":"Maths Sup", "maths-spe":"Maths Spé"}
    difficulties = ["Découverte", "Standard", "Approfondissement", "Difficile", "Challenge"]
    return {"levels": [{"id": level, "label": labels[level]} for level in CURRICULUM_ORDER],
            "difficulties": [{"id": index, "label": label} for index, label in enumerate(difficulties, 1)]}


@router.get("/version")
def get_version() -> dict[str, str]:
    return {"name": APP_NAME, "version": APP_VERSION}


router.include_router(problems_router)
router.include_router(resources_router)
router.include_router(attempts_router)
router.include_router(evaluations_router)
router.include_router(diagnostics_router)
