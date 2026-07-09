"""Application configuration via environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ClauseGuard application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://clauseguard:secret@localhost:5432/clauseguard"
    db_echo: bool = False

    # RabbitMQ
    rabbitmq_url: str = "amqp://clauseguard:secret@localhost:5672/"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "contracts"
    minio_use_ssl: bool = False

    # LLM
    gemini_api_key: str = "gemini-placeholder"
    openai_api_key: str = "sk-placeholder"
    anthropic_api_key: str = "sk-ant-placeholder"
    llm_primary_model: str = "openai/gpt-5.1"
    llm_fallback_model: str = "gemini/gemini-2.5-flash"

    # Rate limiting (token bucket, per client IP)
    rate_limit_enabled: bool = True
    rate_limit_capacity: int = 60  # burst: max tokens in the bucket
    rate_limit_refill_per_second: float = 1.0  # sustained: tokens added per second

    # OpenTelemetry tracing
    otel_enabled: bool = True
    otel_service_name: str = "clauseguard"
    otel_exporter_otlp_endpoint: str = "http://jaeger:4317"

    # Analysis result cache (read-through, completed contracts only)
    analysis_cache_ttl_seconds: int = 3600

    # Semantic clause search relevance thresholds
    search_min_similarity: float = (
        0.25  # absolute floor: rejects noise below the model's random-pair baseline
    )
    search_relative_floor: float = 0.7  # keep hits within this fraction of the query's top score

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @model_validator(mode="after")
    def _guard_production_secrets(self) -> "Settings":
        """Refuse to run in production with insecure default secrets.

        In development the placeholder defaults are fine. In production they
        are a security hole (the app would sign sessions with a value that is
        public in the repo), so we fail fast at startup rather than boot
        silently insecure. This turns a forgotten env var into an obvious
        crash during deploy instead of a latent vulnerability.
        """
        if self.app_env == "production":
            if self.app_secret_key == "change-me-in-production":
                raise ValueError(
                    "APP_SECRET_KEY is still the default value in production. "
                    "Set a real secret via the APP_SECRET_KEY environment variable."
                )
            if len(self.app_secret_key) < 32:
                raise ValueError(
                    "APP_SECRET_KEY is too short for production "
                    f"(got {len(self.app_secret_key)} chars, need at least 32). "
                    "Generate a strong secret, e.g. `openssl rand -hex 32`."
                )
        return self


settings = Settings()
