from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / '.env', extra='ignore')

    app_name: str = '电商运营助手'
    data_dir: Path = BACKEND_DIR / 'data'
    database_url: str = ''
    jwt_secret: str = ''
    access_token_minutes: int = Field(default=480, ge=5, le=1440)
    bootstrap_admin_username: str = 'admin'
    bootstrap_admin_password: str = ''
    demo_enabled: bool = True
    worker_enabled: bool = True
    job_timeout_seconds: int = Field(default=180, ge=5, le=3600)
    job_max_attempts: int = Field(default=3, ge=1, le=10)
    ai_mode: Literal['demo', 'compatible'] = 'demo'
    ai_base_url: str = 'https://api.openai.com/v1'
    ai_api_key: str = ''
    ai_text_model: str = ''
    ai_image_model: str = ''
    video_api_url: str = ''
    video_api_key: str = ''

    @property
    def db_url(self) -> str:
        if self.database_url.startswith('sqlite:///./'):
            return 'sqlite:///' + (BACKEND_DIR / self.database_url[12:]).as_posix()
        return self.database_url or 'sqlite:///' + (self.data_dir / 'operations.db').as_posix()


@lru_cache
def get_settings() -> Settings:
    return Settings()
