from fastapi import APIRouter, HTTPException, status

from app.core.version import APP_NAME, APP_VERSION
from app.services import health

router = APIRouter(prefix="/api")


@router.get("/health")
def get_health() -> dict[str, str]:
    if not health.database_is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "service": "khollelab-api", "database": "unavailable"},
        )
    return {"status": "ok", "service": "khollelab-api", "database": "ok"}


@router.get("/version")
def get_version() -> dict[str, str]:
    return {"name": APP_NAME, "version": APP_VERSION}

