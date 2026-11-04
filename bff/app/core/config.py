from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    projects_api_base_url: str = ""
    projects_api_timeout: float = 15.0

    hardware_api_base_url: str = ""
    hardware_api_key: str = ""
    hardware_api_timeout: float = 15.0

    grpc_host: str = "127.0.0.1"
    grpc_port: int = 50051

    session_secret: str = ""
    session_cookie_secure: bool = False

    users_db_path: str = "/tmp/bff-users.sqlite3"
    local_seed_users: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
