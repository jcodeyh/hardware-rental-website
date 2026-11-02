
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Projects API
    projects_api_base_url: str = ""
    projects_api_timeout: float = 15.0

    # Hardware API
    hardware_api_base_url: str = ""
    hardware_api_timeout: float = 15.0

    # Internal gRPC server
    grpc_host: str = "127.0.0.1"
    grpc_port: int = 50051

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
