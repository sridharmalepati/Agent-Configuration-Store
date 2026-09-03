"""Service configuration loaded from environment."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "qa_automation_service"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/repo_service"
    log_level: str = "INFO"
    cache_maxsize: int = 128
    access_token_encryption_key: str = ""
    strict_repo_url_validation: bool = True
    github_validation_token: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
