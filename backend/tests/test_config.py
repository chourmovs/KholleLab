import pytest
from pydantic import ValidationError
from app.core.config import Settings

def test_fast_token_budget_defaults(monkeypatch):
    monkeypatch.delenv("HF_FAST_MAX_TOKENS", raising=False); monkeypatch.delenv("HF_FAST_RETRY_MAX_TOKENS", raising=False)
    configured = Settings(database_url="sqlite://")
    assert (configured.hf_fast_max_tokens, configured.hf_fast_retry_max_tokens) == (512, 768)

def test_fast_retry_budget_cannot_be_lower_than_initial_budget():
    with pytest.raises(ValidationError, match="HF_FAST_RETRY_MAX_TOKENS must be greater"):
        Settings(database_url="sqlite://", hf_fast_max_tokens=512, hf_fast_retry_max_tokens=511)
