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
    GMAIL_POLL_INTERVAL_SECONDS: int = 120  # 2 minutes
    GMAIL_AUTO_REPLY_ENABLED: bool = False
    GMAIL_MAX_EMAILS_PER_POLL: int = 10

    # LinkedIn OAuth2
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = "http://localhost:8000/integrations/linkedin/callback"
    LINKEDIN_POLL_INTERVAL_SECONDS: int = 120  # 2 minutes

    # Twilio / WhatsApp
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    WHATSAPP_WEBHOOK_URL: str = ""  # Set to public URL (e.g. ngrok) for signature validation
    WHATSAPP_AUTO_REPLY_ENABLED: bool = True
    WHATSAPP_POLL_INTERVAL_SECONDS: int = 120  # 2 minutes
    WHATSAPP_MAX_MESSAGES_PER_POLL: int = 20

    # Facebook / Instagram (Graph API)
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    FACEBOOK_PAGE_ID: str = ""
    FACEBOOK_REDIRECT_URI: str = "http://localhost:8000/integrations/facebook/callback"
    INSTAGRAM_ACCOUNT_ID: str = ""

    # Twitter / X (OAuth 2.0 PKCE)
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""
    TWITTER_REDIRECT_URI: str = "http://localhost:8000/integrations/twitter/callback"

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
