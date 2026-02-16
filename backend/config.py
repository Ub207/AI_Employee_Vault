"""Pydantic-settings configuration loaded from .env."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./backend/vault.db"

    # Vault
    VAULT_PATH: str = "."
    AUTONOMY_LEVEL: str = "MEDIUM"
    SENSITIVITY_THRESHOLD: float = 0.6
    AUTONOMY_MODE: bool = False

    # Gmail OAuth2 placeholders
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/integrations/gmail/callback"

    # Gmail polling / auto-reply
    GMAIL_POLL_INTERVAL_SECONDS: int = 300
    GMAIL_AUTO_REPLY_ENABLED: bool = False
    GMAIL_MAX_EMAILS_PER_POLL: int = 10

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    model_config = {
        "env_file": str(Path(__file__).parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
