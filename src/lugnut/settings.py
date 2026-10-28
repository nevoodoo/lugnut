from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LUGNUT_")

    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = 8080
    secure_cookies: bool = True
    reminder_interval_seconds: int = 3600  # 0 turns the reminder loop off

    @property
    def db_path(self) -> Path:
        return self.data_dir / "lugnut.db"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def attachments_dir(self) -> Path:
        return self.data_dir / "attachments"
