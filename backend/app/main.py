from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.version import APP_NAME, APP_VERSION
from app.services.problem_repository import ProblemRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository = ProblemRepository(settings.problems_dir)
    repository.load()
    app.state.problem_repository = repository
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(router)
