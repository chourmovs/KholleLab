from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.version import APP_NAME, APP_VERSION
from app.api.problems import router as problems_router
from app.api.resources import router as resources_router
from app.api.attempts import router as attempts_router
from app.api.evaluations import router as evaluations_router
from app.core.config import settings
from app.services import health
from app.api.diagnostics import router as diagnostics_router
from app.api.sessions import router as sessions_router
from app.api.profile import router as profile_router
from app.api.auth import router as auth_router
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
def get_curriculum(request: Request) -> dict:
    repository = request.app.state.curriculum_repository
    academic_year = request.app.state.curriculum_academic_year
    return {"academic_year": academic_year, "levels": repository.level_metadata(academic_year),
            "difficulties": [item.model_dump() for item in repository.difficulties]}


@router.get("/version")
def get_version() -> dict[str, str]:
    return {"name": APP_NAME, "version": APP_VERSION}


router.include_router(problems_router)
router.include_router(resources_router)
router.include_router(attempts_router)
router.include_router(evaluations_router)
router.include_router(diagnostics_router)
router.include_router(sessions_router)
router.include_router(profile_router)
router.include_router(auth_router)
