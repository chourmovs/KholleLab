from fastapi import APIRouter, HTTPException, Request, status

from app.core.version import APP_NAME, APP_VERSION
from app.api.problems import router as problems_router
from app.api.attempts import router as attempts_router
from app.api.evaluations import router as evaluations_router
from app.core.config import settings
from app.services import health
from app.domain.problem import CURRICULUM_ORDER

router = APIRouter(prefix="/api")


@router.get("/health")
def get_health(request: Request) -> dict[str, str | int]:
    if not health.database_is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "service": "khollelab-api", "database": "unavailable"},
        )
    repository = request.app.state.problem_repository
    configured = settings.llm_provider == "fake" or bool(settings.openai_api_key)
    return {"status": "ok", "service": "khollelab-api", "database": "ok", "problem_corpus": "ok", "problem_count": repository.count, "curriculum_levels": len({p.curriculum.level for p in repository.list()}), "llm": "configured" if configured else "unconfigured"}


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
router.include_router(attempts_router)
router.include_router(evaluations_router)
