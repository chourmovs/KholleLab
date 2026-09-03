from fastapi import APIRouter, HTTPException, Request, status

from app.core.version import APP_NAME, APP_VERSION
from app.api.problems import router as problems_router
from app.services import health

router = APIRouter(prefix="/api")


@router.get("/health")
def get_health(request: Request) -> dict[str, str | int]:
    if not health.database_is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "service": "khollelab-api", "database": "unavailable"},
        )
    repository = request.app.state.problem_repository
    return {"status": "ok", "service": "khollelab-api", "database": "ok", "problem_corpus": "ok", "problem_count": repository.count}


@router.get("/version")
def get_version() -> dict[str, str]:
    return {"name": APP_NAME, "version": APP_VERSION}


router.include_router(problems_router)
