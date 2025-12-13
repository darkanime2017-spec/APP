# backend/app/core/config.py
import os
import json
import base64
import tempfile
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

    # Google credentials: accept either a file path or a base64 JSON string
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS_B64: str | None = None

    # Other application settings
    FIREBASE_CRED_PATH: str | None = None
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour

    @model_validator(mode='after')
    def assemble_db_connection(self) -> "Settings":
        # 1) Build DATABASE_URL if missing
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

        # 2) If GOOGLE_APPLICATION_CREDENTIALS missing but B64 provided -> write temp file
        if not self.GOOGLE_APPLICATION_CREDENTIALS and self.GOOGLE_APPLICATION_CREDENTIALS_B64:
            try:
                decoded = base64.b64decode(self.GOOGLE_APPLICATION_CREDENTIALS_B64).decode("utf-8")
                # validate JSON
                json.loads(decoded)

                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
                tmp.write(decoded.encode("utf-8"))
                tmp.flush()
                tmp.close()

                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
                self.GOOGLE_APPLICATION_CREDENTIALS = tmp.name
            except Exception as e:
                raise RuntimeError("Failed to decode GOOGLE_APPLICATION_CREDENTIALS_B64: " + str(e)) from e

        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# instantiate settings (runs validator above)
settings = Settings()
