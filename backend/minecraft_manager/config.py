from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 9090
    secret_key: str = "change-me-in-production"
    token_expire_minutes: int = 720
    data_dir: Path = Field(default_factory=lambda: Path("./data"))
    state_file: str = "state.json"
    users_file: str = "users.json"
    logs_dir: str = "logs"
    uploads_dir: str = "uploads"
    model_config = SettingsConfigDict(env_prefix="MCM_", env_file=".env", extra="ignore")

    @property
    def state_path(self) -> Path:
        return self.data_dir / self.state_file

    @property
    def users_path(self) -> Path:
        return self.data_dir / self.users_file

    @property
    def logs_path(self) -> Path:
        return self.data_dir / self.logs_dir

    @property
    def uploads_path(self) -> Path:
        return self.data_dir / self.uploads_dir


settings = Settings()
