import os
import logging
from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache

logger = logging.getLogger("audioshield.config")

class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql://admin:audioshield123@localhost:5432/audioshield"
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    max_duration_seconds: int = 600  # 10 minutes maximum duration
    file_ttl_hours: int = 1
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    @model_validator(mode="after")
    def validate_secret_key(self):
        if self.environment.lower() == "production":
            if not self.secret_key or len(self.secret_key) < 32 or "dev-secret" in self.secret_key:
                raise ValueError(
                    "CRITICAL SECURITY: In production, SECRET_KEY must be a cryptographically secure string of at least 32 characters."
                )
        elif not self.secret_key:
            # In development, generate an ephemeral random key if none specified
            logger.warning(
                "WARNING: No SECRET_KEY set in development. Using an ephemeral fallback key. DO NOT USE IN PRODUCTION."
            )
            object.__setattr__(self, "secret_key", "audioshield-dev-ephemeral-key-replace-in-production")
        return self

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings():
    return Settings()
