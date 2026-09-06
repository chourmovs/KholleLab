from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

class ModelFamily(str, Enum):
    QWEN = "qwen"
    GEMMA = "gemma"


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = Field(description="SQLAlchemy database URL supplied by the environment")
    cors_origins: str = "http://localhost:3000"
    problems_dir: str = "../problems"
    resources_dir: str = "../resources"
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
        return self

    @property
    def evaluation_provider_retry_delays(self) -> tuple[float, ...]:
        values = tuple(float(value.strip()) for value in self.evaluation_provider_retry_delays_seconds.split(","))
        if not values or any(value <= 0 for value in values):
            raise ValueError("EVALUATION_PROVIDER_RETRY_DELAYS_SECONDS must contain positive values")
        return values

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
