from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlparse, urlunparse
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "LiveDrops"
    API_DOMAIN: str = "http://localhost:8000"
    API_V1_STR: str = "/api/v1"
    COOKIE_DOMAIN: Optional[str] = None

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Database Settings (Local)
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # Production Database URL
    DATABASE_URL: Optional[str] = None

    # Redis Storage (Local)
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = 6379

    # Production Redis URL
    REDIS_URL: Optional[str] = None

    # SuperTokens Settings
    SUPERTOKENS_CONNECTION_URI: str = "http://localhost:3567"
    SUPERTOKENS_API_KEY: Optional[str] = None

    # Scheduled Tasks
    CRON_SECRET: str = "fallback-secret-for-local-dev"

    @property
    def async_database_url(self) -> str:
        """Uses the provided URL, or constructs it for local dev"""
        if self.DATABASE_URL:
            # safely parse the URL components
            parsed_url = urlparse(self.DATABASE_URL)

            # rebuild the URL, but pass an empty string for the query parameters
            clean_url: str = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                "",
                parsed_url.fragment
            ))

            # add the asyncpg driver prefix
            if clean_url.startswith("postgres://"):
                return clean_url.replace("postgres://", "postgresql+asyncpg://", 1)
            if clean_url.startswith("postgresql://"):
                return clean_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return clean_url

        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        """Uses the provided URL, or constructs unsecure url"""
        if self.REDIS_URL:
            return self.REDIS_URL

        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Pydantic v2 configuration for reading the .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
