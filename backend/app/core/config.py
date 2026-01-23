from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str = "postgresql://admin:audioshield123@localhost:5432/audioshield"
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    file_ttl_hours: int = 1

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
