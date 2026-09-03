from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.problems import router as problems_router

app = FastAPI(
    title="KholleLab API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(problems_router, prefix="/api/v1")
