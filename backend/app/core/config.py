from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = Field(description="SQLAlchemy database URL supplied by the environment")
    cors_origins: str = "http://localhost:3000"
    problems_dir: str = "../problems"
    llm_provider: str = "fake"
    llm_model: str = ""
    openai_api_key: str | None = None
    llm_timeout_seconds: float = Field(default=90, gt=0)
    local_llm_base_url: str = "http://inference:8080/v1"
    local_llm_model: str = "Qwen/Qwen3-4B-GGUF"
    local_llm_hf_repo: str = "Qwen/Qwen3-4B-GGUF"
    local_llm_quant: str = "Q4_K_M"
    local_llm_context_size: int = Field(default=8192, gt=0)
    local_llm_threads: int = Field(default=6, gt=0)
    local_llm_batch_size: int = Field(default=512, gt=0)
    local_llm_parallel: int = Field(default=1, gt=0)
    local_llm_temperature: float = Field(default=0.2, ge=0)
    local_llm_top_p: float = Field(default=0.9, gt=0, le=1)
    local_llm_max_tokens: int = Field(default=512, gt=0)
    local_llm_timeout_seconds: float = Field(default=90, gt=0)
    log_level: str = "INFO"
    log_rotation: str = "10 MB"
    log_retention: str = "7 days"
    runtime_logs_dir: str = "/runtime-logs"
    diagnostics_enabled: bool = False
    diagnostics_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
