from functools import lru_cache
from ipaddress import ip_address
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

class ModelFamily(str, Enum):
    QWEN = "qwen"
    GEMMA = "gemma"


def canonicalize_origin(value: str) -> str:
    """Return the canonical HTTP origin represented by a configured/header value."""
    candidate = value.strip()
    if not candidate or "*" in candidate:
        raise ValueError("origins must be exact HTTP(S) origins; wildcards are not allowed")
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"invalid origin {value!r}") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"invalid origin {value!r}: an http(s) scheme and hostname are required")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError(f"invalid origin {value!r}: paths, credentials, queries and fragments are not allowed")
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower()
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError(f"invalid origin hostname in {value!r}") from exc
    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and port != {"http": 80, "https": 443}[scheme]:
        host = f"{host}:{port}"
    return f"{scheme}://{host}"


def _origin_list(value: str) -> list[str]:
    return [canonicalize_origin(origin) for origin in value.split(",") if origin.strip()]


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = Field(description="SQLAlchemy database URL supplied by the environment")
    cors_origins: str = "http://localhost:3000"
    auth_trusted_origins: str = ""
    problems_dir: str = "../problems"
    resources_dir: str = "../resources"
    curriculum_dir: str = "../curriculum"
    curriculum_academic_year: str | None = None
    llm_provider: str = "huggingface"
    llm_model: str = ""
    openai_api_key: str | None = None
    llm_timeout_seconds: float = Field(default=90, gt=0)
    hf_token: str | None = None
    hf_router_base_url: str = "https://router.huggingface.co/v1"
    llm_model_family: ModelFamily = ModelFamily.QWEN
    hf_qwen_fast_model: str = "Qwen/Qwen3-8B:nscale"
    hf_qwen_deep_model: str = "Qwen/Qwen3-32B:nscale"
    hf_gemma_fast_model: str = "google/gemma-3-12b-it:deepinfra"
    hf_gemma_deep_model: str = "google/gemma-3-27b-it:deepinfra"
    hf_timeout_seconds: float = Field(default=60, gt=0)
    hf_fast_max_tokens: int = Field(default=512, gt=0)
    hf_fast_retry_max_tokens: int = Field(default=768, gt=0)
    hf_examiner_audit_max_tokens: int = Field(default=1024, gt=0)
    hf_examiner_adjudication_max_tokens: int = Field(default=1536, gt=0)
    hf_request_max_attempts: int = Field(default=3, ge=1, le=10)
    hf_retry_base_seconds: float = Field(default=1.0, ge=0)
    hf_retry_max_seconds: float = Field(default=8.0, gt=0, le=60)
    hf_retry_jitter_seconds: float = Field(default=0.5, ge=0, le=10)
    evaluation_provider_max_retries: int = Field(default=4, ge=0, le=10)
    evaluation_provider_retry_delays_seconds: str = "15,45,120,300"
    evaluation_worker_poll_seconds: float = Field(default=1, gt=0)
    evaluation_stale_seconds: int = Field(default=180, gt=0)
    evaluation_worker_heartbeat_seconds: float = Field(default=10, gt=0, le=60)
    evaluation_worker_health_max_age_seconds: float = Field(default=45, gt=0)
    evaluation_worker_heartbeat_path: str = "/tmp/khollelab-evaluation-worker.heartbeat"
    log_level: str = "INFO"
    log_rotation: str = "10 MB"
    log_retention: str = "7 days"
    runtime_logs_dir: str = "/runtime-logs"
    log_process_role: str = "api"
    diagnostics_enabled: bool = False
    diagnostics_token: str | None = None
    proactive_tutor_enabled: bool = True
    tutor_initial_grace_seconds: int = 45
    tutor_idle_after_change_seconds: int = 6
    tutor_min_assessment_interval_seconds: int = 25
    tutor_intervention_cooldown_seconds: int = 45
    tutor_stalled_seconds: int = 90
    tutor_max_auto_assessments_per_attempt: int = 12
    tutor_auto_max_help_level: int = 3
    tutor_resource_recommendations_enabled: bool = True
    tutor_resource_auto_min_confidence: float = Field(default=.90, ge=0, le=1)
    tutor_resource_manual_min_confidence: float = Field(default=.85, ge=0, le=1)
    llm_problem_generation_enabled: bool = False
    llm_problem_pool_target: int = Field(default=8, ge=1, le=100)
    llm_problem_max_generation_attempts: int = Field(default=3, ge=1, le=10)
    llm_problem_diversity_context_limit: int = Field(default=8, ge=0, le=20)
    llm_problem_near_duplicate_threshold: float = Field(default=.88, ge=.5, le=1)
    llm_problem_generator_family: ModelFamily = ModelFamily.QWEN
    llm_problem_critic_family: ModelFamily = ModelFamily.GEMMA
    auth_session_days: int = Field(default=30, ge=1, le=365)
    auth_cookie_name: str = "khollelab_session"
    auth_password_min_length: int = Field(default=12, ge=8, le=128)
    auth_login_max_failures: int = Field(default=5, ge=1, le=100)
    auth_login_window_seconds: int = Field(default=300, ge=10)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_fast_token_budgets(self) -> "Settings":
        if self.hf_fast_retry_max_tokens < self.hf_fast_max_tokens:
            raise ValueError("HF_FAST_RETRY_MAX_TOKENS must be greater than or equal to HF_FAST_MAX_TOKENS")
        if self.hf_retry_max_seconds < self.hf_retry_base_seconds:
            raise ValueError("HF_RETRY_MAX_SECONDS must be greater than or equal to HF_RETRY_BASE_SECONDS")
        delays = self.evaluation_provider_retry_delays
        if len(delays) < self.evaluation_provider_max_retries:
            raise ValueError("EVALUATION_PROVIDER_RETRY_DELAYS_SECONDS must cover every durable retry")
        if self.evaluation_worker_health_max_age_seconds <= self.evaluation_worker_heartbeat_seconds:
            raise ValueError("worker health maximum age must exceed heartbeat interval")
        if self.log_process_role not in {"api", "worker"}:
            raise ValueError("LOG_PROCESS_ROLE must be api or worker")
        # Resolve both lists during validation so malformed deployment values fail at startup.
        self.cors_origin_list
        trusted = self.auth_trusted_origin_list
        if self.app_env.lower() in {"prod", "production"}:
            public_https = [origin for origin in trusted if origin.startswith("https://") and not _is_local_origin(origin)]
            if not public_https:
                raise ValueError(
                    "production requires AUTH_TRUSTED_ORIGINS (or its CORS_ORIGINS fallback) "
                    "to contain at least one public HTTPS origin"
                )
        return self

    @property
    def evaluation_provider_retry_delays(self) -> tuple[float, ...]:
        values = tuple(float(value.strip()) for value in self.evaluation_provider_retry_delays_seconds.split(","))
        if not values or any(value <= 0 for value in values):
            raise ValueError("EVALUATION_PROVIDER_RETRY_DELAYS_SECONDS must contain positive values")
        return values

    @property
    def cors_origin_list(self) -> list[str]:
        return _origin_list(self.cors_origins)

    @property
    def auth_trusted_origin_list(self) -> list[str]:
        return _origin_list(self.auth_trusted_origins or self.cors_origins)


def _is_local_origin(origin: str) -> bool:
    hostname = urlsplit(origin).hostname or ""
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
