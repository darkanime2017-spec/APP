"""
Application Configuration Management.

This module uses Pydantic's BaseSettings to load and validate configuration
from environment variables. It centralizes all configuration parameters,
making them easily accessible throughout the application.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loads environment variables for the application."""

    # Database settings - will be constructed if not provided directly
    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    RAILWAY_TCP_PROXY_DOMAIN: str | None = None # Public Host
    RAILWAY_TCP_PROXY_PORT: int | None = None   # Public Port
    POSTGRES_DB: str | None = None

    # Other application settings
    GOOGLE_CREDENTIALS_PATH: str
    FIREBASE_CRED_PATH: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour

    @model_validator(mode='after')
    def assemble_db_connection(self) -> 'Settings':
        if self.DATABASE_URL is None:
            if all([self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.RAILWAY_TCP_PROXY_DOMAIN, self.RAILWAY_TCP_PROXY_PORT, self.POSTGRES_DB]):
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                    f"{self.RAILWAY_TCP_PROXY_DOMAIN}:{self.RAILWAY_TCP_PROXY_PORT}/{self.POSTGRES_DB}"
                )
        return self

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')


settings = Settings()