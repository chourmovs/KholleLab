import threading
import time
from collections import defaultdict, deque

from email_validator import EmailNotValidError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.attempts import session as db_session
from app.core.config import settings
from app.core.logging import component_logger
from app.models.auth import AuthSession, UserAccount
from app.models.attempt import utcnow
from app.models.learning_session import LearningSession
from app.schemas.auth import AccountView, ChangePasswordRequest, LoginRequest, RegisterRequest
from app.services.authentication import (claim_anonymous_history, create_auth_session, normalize_email,
                                         password_hash, revoke_sessions)

router = APIRouter(prefix="/auth", tags=["authentication"])
log = component_logger("authentication")
_failures: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()

def reject_cross_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origin_list:
        raise HTTPException(403, "Origine de la requête refusée.")

def anonymous_count(db: Session, request: Request) -> int:
    return db.scalar(select(func.count()).select_from(LearningSession).where(
        LearningSession.learner_id == request.state.anonymous_learner_id)) or 0

def view(user: UserAccount | None, count: int) -> AccountView:
    if not user:
        return AccountView(authenticated=False, anonymous_sessions_available=count)
    return AccountView(authenticated=True, email=user.email, display_name=user.display_name,
                       created_at=user.created_at, anonymous_sessions_available=count)

def set_cookie(response: Response, raw: str):
    response.set_cookie(settings.auth_cookie_name, raw, httponly=True, secure=settings.app_env.lower() in {"prod", "production"},
                        samesite="lax", path="/", max_age=settings.auth_session_days * 86400)

def validate_password(value: str):
    if not settings.auth_password_min_length <= len(value) <= 128:
        raise HTTPException(422, f"Le mot de passe doit contenir entre {settings.auth_password_min_length} et 128 caractères.")

def normalized_or_422(value: str):
    try: return normalize_email(value)
    except EmailNotValidError: raise HTTPException(422, "Adresse e-mail invalide.")

def rate_limited(key: str) -> bool:
    now = time.monotonic()
    with _lock:
        values = _failures[key]
        while values and values[0] <= now - settings.auth_login_window_seconds: values.popleft()
        return len(values) >= settings.auth_login_max_failures

def fail(key: str):
    with _lock: _failures[key].append(time.monotonic())

@router.post("/register", response_model=AccountView, status_code=201)
def register(body: RegisterRequest, request: Request, response: Response, db: Session = Depends(db_session)):
    reject_cross_origin(request); validate_password(body.password)
    email, normalized = normalized_or_422(body.email)
    if rate_limited("register:" + normalized): raise HTTPException(429, "Trop de tentatives. Réessayez plus tard.")
    user = UserAccount(email=email, email_normalized=normalized, password_hash=password_hash.hash(body.password),
                       display_name=body.display_name.strip() if body.display_name and body.display_name.strip() else None)
    db.add(user)
    try:
        db.flush()
        if body.claim_anonymous_history: claim_anonymous_history(db, request.state.anonymous_learner_id, user.learner_id)
        _, raw = create_auth_session(db, user); db.commit()
    except IntegrityError:
        db.rollback(); fail("register:" + normalized)
        raise HTTPException(409, "Un compte utilise déjà cette adresse e-mail.")
    set_cookie(response, raw); log.info("event=account_registered account_id={}", user.id)
    return view(user, anonymous_count(db, request))

@router.post("/login", response_model=AccountView)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(db_session)):
    reject_cross_origin(request)
    try: _, normalized = normalize_email(body.email)
    except EmailNotValidError: normalized = body.email.strip().casefold()
    key = "login:" + normalized
    if rate_limited(key): raise HTTPException(429, "Trop de tentatives. Réessayez plus tard.")
    user = db.scalar(select(UserAccount).where(UserAccount.email_normalized == normalized, UserAccount.disabled_at.is_(None)))
    if not user or not password_hash.verify(body.password, user.password_hash):
        fail(key); log.info("event=login_failed category=invalid_credentials")
        raise HTTPException(401, "Adresse e-mail ou mot de passe incorrect.")
    _, raw = create_auth_session(db, user); db.commit(); set_cookie(response, raw)
    log.info("event=login_succeeded account_id={}", user.id)
    return view(user, anonymous_count(db, request))

@router.get("/me", response_model=AccountView)
def me(request: Request, db: Session = Depends(db_session)):
    return view(request.state.user, anonymous_count(db, request))

def require_user(request: Request) -> UserAccount:
    if not request.state.user: raise HTTPException(401, "Authentification requise.")
    return request.state.user

@router.post("/claim-anonymous")
def claim(request: Request, db: Session = Depends(db_session)):
    reject_cross_origin(request); user = require_user(request)
    count = claim_anonymous_history(db, request.state.anonymous_learner_id, user.learner_id); db.commit()
    log.info("event=anonymous_history_claimed account_id={} session_count={}", user.id, count)
    return {"claimed_sessions": count}

@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(db_session)):
    reject_cross_origin(request)
    if request.state.auth_session:
        request.state.auth_session.revoked_at = utcnow(); db.commit(); log.info("event=logout account_id={}", request.state.auth_session.user_id)
    response.delete_cookie(settings.auth_cookie_name, path="/", secure=settings.app_env.lower() in {"prod", "production"}, samesite="lax")

@router.post("/logout-all", status_code=204)
def logout_all(request: Request, response: Response, db: Session = Depends(db_session)):
    reject_cross_origin(request); user = require_user(request); revoke_sessions(db, user.id); db.commit()
    response.delete_cookie(settings.auth_cookie_name, path="/", secure=settings.app_env.lower() in {"prod", "production"}, samesite="lax")
    log.info("event=logout_all account_id={}", user.id)

@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordRequest, request: Request, db: Session = Depends(db_session)):
    reject_cross_origin(request); user = require_user(request); validate_password(body.new_password)
    if not password_hash.verify(body.current_password, user.password_hash): raise HTTPException(400, "Mot de passe actuel incorrect.")
    user.password_hash = password_hash.hash(body.new_password); user.updated_at = utcnow()
    revoke_sessions(db, user.id, request.state.auth_session.id); db.commit()
    log.info("event=password_changed account_id={}", user.id)
