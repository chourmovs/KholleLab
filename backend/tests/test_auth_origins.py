from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.attempts import session
from app.core.config import settings
from app.db.base import Base
from app.main import app


@pytest.fixture()
def auth_client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    app.dependency_overrides[session] = lambda: testing_session()
    monkeypatch.setattr("app.services.learner_identity.SessionLocal", testing_session)
    monkeypatch.setattr(settings, "problems_dir", str(Path(__file__).resolve().parents[2] / "problems"))
    monkeypatch.setattr(settings, "auth_trusted_origins", "https://kholle.example.test")
    monkeypatch.setattr(settings, "app_env", "development")
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(session, None)
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client, origin="https://kholle.example.test", email="student@example.com"):
    return client.post(
        "/api/auth/register",
        headers={"Origin": origin},
        json={
            "email": email,
            "password": "a-secure-password",
            "claim_anonymous_history": False,
        },
    )


def test_public_origin_registers_and_logs_in(auth_client):
    registered = register(auth_client)
    assert registered.status_code == 201, registered.text
    auth_client.post("/api/auth/logout", headers={"Origin": "https://kholle.example.test"})
    logged_in = auth_client.post(
        "/api/auth/login",
        headers={"Origin": "HTTPS://KHOLLE.EXAMPLE.TEST/"},
        json={"email": "student@example.com", "password": "a-secure-password"},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["authenticated"] is True


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "https://kholle.example.test.evil.example",
        "http://kholle.example.test",
        "https://evil-kholle.example.test",
    ],
)
def test_foreign_and_lookalike_origins_are_rejected(auth_client, origin):
    response = register(auth_client, origin=origin, email=f"student{abs(hash(origin))}@example.com")
    assert response.status_code == 403
    assert response.json()["detail"] == "Origine de la requête refusée."


def test_rejected_origin_log_contains_deployment_context(auth_client, monkeypatch):
    auth_log = Mock()
    monkeypatch.setattr("app.api.auth.log", auth_log)

    response = register(auth_client, origin="https://evil.example", email="logged@example.com")

    assert response.status_code == 403
    auth_log.warning.assert_called_once_with(
        "event=auth_origin_rejected origin={} trusted_origins={} method={} path={}",
        "https://evil.example",
        ["https://kholle.example.test"],
        "POST",
        "/api/auth/register",
    )


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/auth/register", {"email": "mutation@example.test", "password": "a-secure-password", "claim_anonymous_history": False}),
        ("/api/auth/login", {"email": "mutation@example.test", "password": "a-secure-password"}),
        ("/api/auth/claim-anonymous", None),
        ("/api/auth/logout", None),
        ("/api/auth/logout-all", None),
        ("/api/auth/change-password", {"current_password": "a-secure-password", "new_password": "another-secure-password"}),
    ],
)
def test_every_auth_mutation_rejects_a_foreign_origin(auth_client, path, body):
    response = auth_client.post(path, headers={"Origin": "https://evil.example"}, json=body)
    assert response.status_code == 403
    assert response.json()["detail"] == "Origine de la requête refusée."


def test_missing_origin_preserves_non_browser_compatibility(auth_client):
    assert auth_client.post(
        "/api/auth/register",
        json={"email": "cli@example.com", "password": "a-secure-password", "claim_anonymous_history": False},
    ).status_code == 201


def test_production_auth_cookie_is_secure_lax_httponly_and_root_scoped(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    response = register(auth_client, email="cookie@example.com")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie


def test_local_development_origin_still_works(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "auth_trusted_origins", "")
    monkeypatch.setattr(settings, "cors_origins", "http://localhost:3000")
    response = register(auth_client, origin="http://localhost:3000", email="local@example.com")
    assert response.status_code == 201
