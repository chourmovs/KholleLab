import hashlib
import secrets
from datetime import timedelta

from email_validator import validate_email
from pwdlib import PasswordHash
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auth import AuthSession, UserAccount
from app.models.attempt import utcnow
from app.models.learning_session import LearningSession, LearningSessionStatus

password_hash = PasswordHash.recommended()


def normalize_email(value: str) -> tuple[str, str]:
    result = validate_email(value.strip(), check_deliverability=False)
    display = result.normalized
    return display, display.casefold()


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_auth_session(db: Session, user: UserAccount) -> tuple[AuthSession, str]:
    raw = secrets.token_urlsafe(32)
    now = utcnow()
    value = AuthSession(user_id=user.id, token_hash=hash_token(raw), created_at=now,
                        last_seen_at=now, expires_at=now + timedelta(days=settings.auth_session_days))
    db.add(value)
    db.flush()
    return value, raw


def claim_anonymous_history(db: Session, anonymous_learner_id, account_learner_id) -> int:
    """Move session ownership without copying descendants; account active sessions win conflicts."""
    if anonymous_learner_id == account_learner_id:
        return 0
    anonymous = list(db.scalars(select(LearningSession).where(LearningSession.learner_id == anonymous_learner_id)))
    if not anonymous:
        return 0
    active_keys = set(db.scalars(select(LearningSession.active_problem_key).where(
        LearningSession.learner_id == account_learner_id, LearningSession.active_problem_key.is_not(None))))
    now = utcnow()
    for item in anonymous:
        if item.active_problem_key in active_keys:
            item.status = LearningSessionStatus.ABANDONED
            item.active_problem_key = None
            item.updated_at = now
        item.learner_id = account_learner_id
    db.flush()
    return len(anonymous)


def revoke_sessions(db: Session, user_id, except_id=None) -> None:
    query = update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    if except_id is not None:
        query = query.where(AuthSession.id != except_id)
    db.execute(query.values(revoked_at=utcnow()))
