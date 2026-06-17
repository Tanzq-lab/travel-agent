from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Travel Agent MVP"
    app_env: str = "local"
    database_path: Path = Path("data/travel_agent.sqlite3")
    vector_store_path: Path = Path("data/vector_store")
    default_use_mock: bool = True

    openai_api_key: str | None = Field(default=None, repr=False)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"

    media_crawler_command: str | None = None
    media_crawler_root: Path = Path("external/MediaCrawler")
    media_crawler_runner: str = "uv run"
    media_crawler_login_type: str = "qrcode"
    media_crawler_save_option: str = "jsonl"
    media_crawler_headless: bool = False
    media_crawler_workdir: Path | None = None
    media_crawler_sleep_seconds: float = 1.0
    media_crawler_rate_limit_per_minute: int = 10
    media_crawler_timeout_seconds: int = 120
    media_crawler_runs_path: Path = Path("data/media_crawler_runs")
    media_crawler_require_initialized: bool = True
    media_crawler_init_status_path: Path = Path("data/media_crawler_init/status.json")

    max_queries: int = 14
    min_document_length: int = 20


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
