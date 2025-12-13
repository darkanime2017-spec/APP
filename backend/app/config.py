from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    RAILWAY_TCP_PROXY_DOMAIN: str | None = None
    RAILWAY_TCP_PROXY_PORT: int | None = None
    POSTGRES_DB: str | None = None

    # Other application settings
    GOOGLE_CREDENTIALS_PATH: str | None = None  # optional now
    GOOGLE_APPLICATION_CREDENTIALS_B64: str | None = None  # add this
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
