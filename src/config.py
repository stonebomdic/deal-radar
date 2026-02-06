from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Environment
    environment: str = "development"  # "development" or "production"

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

    # Notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""
    notification_enabled: bool = True

    # CORS (comma-separated origins, empty means localhost only)
    cors_origins: str = ""

    # Admin
    admin_api_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
