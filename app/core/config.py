from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "Live Auction Platform"
    API_V1_STR: str = "/api/v1"

    # Database Settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    # Redis Storage
    REDIS_HOST: str
    REDIS_PORT: int

    # SuperTokens Settings
    SUPERTOKENS_CONNECTION_URI: str
    SUPERTOKENS_API_KEY: Optional[str] = None

    @property
    def async_database_url(self) -> str:
        """Constructs the asyncpg connection string dynamically"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        """Constructs the Redis connection string"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Pydantic v2 configuration for reading the .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
