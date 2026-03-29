from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_allowed_origins: str = "http://localhost,http://localhost:5173,https://rag.beestack.vn"

    # GitHub webhook
    github_webhook_enabled: bool = False
    github_webhook_secret: Optional[str] = None
    github_webhook_repo_path: str = "."
    github_webhook_branch: str = "main"

    # PostgreSQL
    postgres_user: str = "rag_user"
    postgres_password: str = "rag_password"
    postgres_db: str = "rag_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: Optional[str] = None

    # Provider selection
    embedding_provider: str = "ollama"
    chat_provider: str = "groq"

    # Ollama embedding
    ollama_base_url: str = "http://localhost:11434"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"

    # Cohere
    cohere_api_key: Optional[str] = None
    cohere_base_url: str = "https://api.cohere.com/v2"

    # Embedding
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 1536

    # Groq LLM
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"

    # MinIO
    minio_host: str = "localhost"
    minio_port: int = 9000
    minio_access_key: str = "rag_minio_user"
    minio_secret_key: str = "rag_minio_secret"
    minio_bucket: str = "rag-documents"
    minio_secure: bool = False
    max_upload_size_mb: int = 10

    @property
    def async_database_url(self) -> str:
        if self.database_url:
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Used by Alembic migrations (synchronous)."""
        if self.database_url:
            return self.database_url.replace("postgresql+asyncpg://", "postgresql://")
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
