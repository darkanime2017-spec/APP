from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    RAILWAY_TCP_PROXY_DOMAIN: str | None = None
    RAILWAY_TCP_PROXY_PORT: int | None = None
    POSTGRES_DB: str | None = None

    GOOGLE_APPLICATION_CREDENTIALS: str
    DRIVE_ROOT_FOLDER_ID: str | None = None
    DISABLE_DRIVE_IN_DEV: bool = False

    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if self.DATABASE_URL is None:
            if all([
                self.POSTGRES_USER,
                self.POSTGRES_PASSWORD,
                self.RAILWAY_TCP_PROXY_DOMAIN,
                self.RAILWAY_TCP_PROXY_PORT,
                self.POSTGRES_DB,
            ]):
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                    f"{self.RAILWAY_TCP_PROXY_DOMAIN}:{self.RAILWAY_TCP_PROXY_PORT}/{self.POSTGRES_DB}"
                )
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
