from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.version import APP_NAME, APP_VERSION
from app.services.problem_repository import ProblemRepository
from app.services.resource_repository import ResourceRepository, validate_problem_resource_refs
from app.services.resource_resolver import ResourceResolver
from app.core.logging import configure_logging, component_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    component_logger("application").info("Startup version={} env={}", APP_VERSION, settings.app_env)
    component_logger("inference").info("Provider={} family={}", settings.llm_provider, settings.llm_model_family.value)
    repository = ProblemRepository(settings.problems_dir)
    repository.load()
    resource_repository = ResourceRepository(settings.resources_dir)
    resource_repository.load()
    validate_problem_resource_refs(repository, resource_repository)
    curriculum_levels = len({problem.curriculum.level for problem in repository.list()})
    component_logger("application").info(
        "content_corpus_loaded problem_count={} resource_count={} curriculum_levels={}",
        repository.count, resource_repository.count, curriculum_levels,
    )
    app.state.problem_repository = repository
    app.state.resource_repository = resource_repository
    app.state.resource_resolver = ResourceResolver(resource_repository)
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
app.include_router(router)
