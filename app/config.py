from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from uuid import UUID

DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")
class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""
    database_url: str = "postgresql://postgres:postgres@localhost:5432/univera"
    secret_key: str = "CHANGE_ME"  # Replace in production
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    file_storage_path: str = str(Path("files"))
    
    debug: bool = True
    allowed_hosts: str = "localhost"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow"  # ✅ To ignore extra env vars like DEBUG, ALLOWED_HOSTS
    )

settings = Settings()
