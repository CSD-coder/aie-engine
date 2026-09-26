from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite:///./aie.db"
    redis_url: str = "redis://localhost:6379/0"
    object_storage_endpoint: str | None = None
    object_storage_bucket: str = "aie-engine"
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None
    object_storage_region: str = "us-east-1"
    hf_token: str | None = None
    engine_api_secret: str = "development-secret-change-me"
    engine_api_keys_json: str = "{}"
    cors_origins: str = "https://app.aiencrypt.com"
    result_retention_hours: int = 168

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
