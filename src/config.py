"""Supply Chain Optimizer - Configuration Module."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="supply-chain-optimizer")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # API Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # LLM Configuration
    # Supports: "ollama" (open source), "openai", "anthropic"
    llm_provider: Literal["ollama", "openai", "anthropic"] = Field(default="ollama")
    
    # Ollama (open source, local)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama4")
    
    # OpenAI (optional, for cloud deployments)
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4o")
    
    # Anthropic (optional)
    anthropic_api_key: str | None = Field(default=None)
    anthropic_model: str = Field(default="claude-3-sonnet-20240229")

    # Vector Store (ChromaDB - open source)
    chroma_persist_directory: str = Field(default="./data/chroma")

    # Database
    # SQLite for development (open source)
    sqlite_database_url: str = Field(
        default="sqlite+aiosqlite:///./data/supply_chain.db"
    )
    # PostgreSQL for production (open source)
    database_url: str | None = Field(default=None)

    # External APIs (optional)
    openweather_api_key: str | None = Field(default=None)
    google_maps_api_key: str | None = Field(default=None)

    # Redis (open source, optional)
    redis_url: str = Field(default="redis://localhost:6379/0")

    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL (PostgreSQL if set, else SQLite)."""
        return self.database_url or self.sqlite_database_url


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
