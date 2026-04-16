"""Application configuration via environment variables."""

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
    llm_primary_model: str = "gpt-5.1"
    llm_fallback_model: str = "gemini/gemini-2.5-flash"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"


settings = Settings()
