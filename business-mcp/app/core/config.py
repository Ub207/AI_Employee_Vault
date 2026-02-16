"""
Central configuration — loads from .env via pydantic-settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root of the business-mcp package (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Server ──
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8005

    # ── SMTP ──
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""

    # ── LinkedIn ──
    linkedin_access_token: str = ""
    linkedin_person_urn: str = ""

    # ── Logging ──
    log_file: str = "vault/logs/business.log"
    log_level: str = "INFO"

    @property
    def log_file_path(self) -> Path:
        """Return an absolute path to the log file."""
        p = Path(self.log_file)
        if not p.is_absolute():
            p = BASE_DIR / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
