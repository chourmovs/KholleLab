import pytest
from pydantic import ValidationError
from app.core.config import Settings, canonicalize_origin

def test_fast_token_budget_defaults(monkeypatch):
    monkeypatch.delenv("HF_FAST_MAX_TOKENS", raising=False); monkeypatch.delenv("HF_FAST_RETRY_MAX_TOKENS", raising=False)
    configured = Settings(database_url="sqlite://")
    assert (configured.hf_fast_max_tokens, configured.hf_fast_retry_max_tokens) == (512, 768)

def test_fast_retry_budget_cannot_be_lower_than_initial_budget():
    with pytest.raises(ValidationError, match="HF_FAST_RETRY_MAX_TOKENS must be greater"):
        Settings(database_url="sqlite://", hf_fast_max_tokens=512, hf_fast_retry_max_tokens=511)


def test_origin_normalization_and_auth_fallback():
    configured = Settings(database_url="sqlite://", cors_origins="HTTPS://Example.ORG/,http://localhost:3000/")
    assert configured.cors_origin_list == ["https://example.org", "http://localhost:3000"]
    assert configured.auth_trusted_origin_list == configured.cors_origin_list
    assert canonicalize_origin("https://EXAMPLE.org:443/") == "https://example.org"


@pytest.mark.parametrize("origin", ["*", "https://*", "*.duckdns.org", "https://example.org/path", "example.org"])
def test_malformed_or_non_exact_configured_origins_are_rejected(origin):
    with pytest.raises(ValidationError, match="origin"):
        Settings(database_url="sqlite://", auth_trusted_origins=origin)


def test_explicit_auth_trusted_origins_are_separate_from_cors():
    configured = Settings(database_url="sqlite://", cors_origins="http://localhost:3000",
                          auth_trusted_origins="https://kholle.example.test")
    assert configured.cors_origin_list == ["http://localhost:3000"]
    assert configured.auth_trusted_origin_list == ["https://kholle.example.test"]


@pytest.mark.parametrize("origins", ["", "http://localhost:3000", "https://localhost"])
def test_production_requires_a_public_https_trusted_origin(origins):
    with pytest.raises(ValidationError, match="public HTTPS origin"):
        Settings(database_url="sqlite://", app_env="production", cors_origins=origins)
