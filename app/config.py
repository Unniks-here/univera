from pydantic import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""
    database_url: str = "postgresql://postgres:postgres@localhost:5432/univera"
    secret_key: str = "CHANGE_ME"  # Replace in production
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    file_storage_path: str = str(Path("files"))

    class Config:
        env_file = ".env"

settings = Settings()
