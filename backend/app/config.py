from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Pilot Resource Tracker API'
    api_prefix: str = '/api'
    debug: bool = False

    database_url: str = Field(
        default='postgresql+psycopg://postgres:postgres@localhost:5432/pilot_tracker',
        alias='DATABASE_URL',
    )

    cors_origins: str = Field(default='http://localhost:5173', alias='CORS_ORIGINS')

    work_hours_per_week: float = Field(default=40.0, alias='WORK_HOURS_PER_WEEK')
    cost_per_minute: float = Field(default=23.0, alias='COST_PER_MINUTE')

    trino_host: str | None = Field(default=None, alias='TRINO_HOST')
    trino_port: int = Field(default=8080, alias='TRINO_PORT')
    trino_user: str | None = Field(default=None, alias='TRINO_USER')
    trino_password: str | None = Field(default=None, alias='TRINO_PASSWORD')
    trino_catalog: str | None = Field(default=None, alias='TRINO_CATALOG')
    trino_schema: str | None = Field(default=None, alias='TRINO_SCHEMA')
    trino_http_scheme: str = Field(default='http', alias='TRINO_HTTP_SCHEME')

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
