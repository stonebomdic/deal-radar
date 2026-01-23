from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/credit_cards.db"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Crawler
    crawler_delay_min: int = 2
    crawler_delay_max: int = 5
    crawler_max_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
