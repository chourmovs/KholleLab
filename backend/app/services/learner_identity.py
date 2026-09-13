import uuid
from datetime import timedelta, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.auth import AuthSession, UserAccount
from app.models.attempt import utcnow
from app.services.authentication import hash_token
from sqlalchemy import select
from sqlalchemy.orm import joinedload

COOKIE_NAME = "khollelab_learner"


def learner_id(request: Request) -> uuid.UUID:
    """Return the resolved account learner identity or anonymous browser identity."""
    return request.state.learner_id


class LearnerIdentityMiddleware(BaseHTTPMiddleware):
    """Resolve an independent anonymous cookie and an optional server-side account session."""

    async def dispatch(self, request: Request, call_next):
        raw = request.cookies.get(COOKIE_NAME)
        try:
            value = uuid.UUID(raw) if raw else uuid.uuid4()
        except (ValueError, AttributeError):
            value = uuid.uuid4()
        anonymous_value = value
        request.state.anonymous_learner_id = anonymous_value
        request.state.user = None
        request.state.auth_session = None
        stale_auth = False
        token = request.cookies.get(settings.auth_cookie_name)
        if token:
            with SessionLocal() as db:
                auth = db.scalar(select(AuthSession).options(joinedload(AuthSession.user)).where(
                    AuthSession.token_hash == hash_token(token), AuthSession.revoked_at.is_(None)))
                now = utcnow()
                # SQLite can return naive datetimes even for timezone=True.
                expires = auth.expires_at.replace(tzinfo=timezone.utc) if auth and auth.expires_at.tzinfo is None else (auth.expires_at if auth else None)
                if auth and expires > now and auth.user.disabled_at is None:
                    request.state.user = auth.user
                    request.state.auth_session = auth
                    value = auth.user.learner_id
                    last_seen = auth.last_seen_at.replace(tzinfo=timezone.utc) if auth.last_seen_at.tzinfo is None else auth.last_seen_at
                    if last_seen < now - timedelta(hours=1):
                        auth.last_seen_at = now; db.commit()
                else:
                    stale_auth = True
        request.state.learner_id = value
        response = await call_next(request)
        # Authentication changes only the resolved request identity. Never
        # replace the independent anonymous-browser cookie with account identity,
        # otherwise logout could expose the account's claimed history.
        if raw != str(anonymous_value):
            response.set_cookie(
                COOKIE_NAME, str(anonymous_value), httponly=True, samesite="lax", path="/",
                secure=settings.app_env.lower() in {"production", "prod"},
            )
        if stale_auth:
            response.delete_cookie(settings.auth_cookie_name, path="/", samesite="lax",
                                   secure=settings.app_env.lower() in {"production", "prod"})
        return response
