import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

COOKIE_NAME = "khollelab_learner"


def learner_id(request: Request) -> uuid.UUID:
    """Return the opaque browser identity established by the middleware."""
    return request.state.learner_id


class LearnerIdentityMiddleware(BaseHTTPMiddleware):
    """Provide anonymous browser isolation; this is not authentication."""

    async def dispatch(self, request: Request, call_next):
        raw = request.cookies.get(COOKIE_NAME)
        try:
            value = uuid.UUID(raw) if raw else uuid.uuid4()
        except (ValueError, AttributeError):
            value = uuid.uuid4()
        request.state.learner_id = value
        response = await call_next(request)
        if raw != str(value):
            response.set_cookie(
                COOKIE_NAME, str(value), httponly=True, samesite="lax", path="/",
                secure=settings.app_env.lower() in {"production", "prod"},
            )
        return response
