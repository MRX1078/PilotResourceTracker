from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _normalize_trino_settings(data: object) -> object:
    if not isinstance(data, dict):
        return data
    normalized = dict(data)
    for field in (
        'trino_host',
        'trino_user',
        'trino_password',
        'trino_catalog',
        'trino_schema',
        'trino_http_scheme',
    ):
        value = normalized.get(field)
        if isinstance(value, str):
            stripped = value.strip()
            normalized[field] = stripped or None
    return normalized


class TrinoSettings(BaseModel):
    trino_host: str | None = Field(default=None, max_length=255)
    trino_port: int | None = Field(default=None, ge=1, le=65535)
    trino_user: str | None = Field(default=None, max_length=255)
    trino_password: str | None = Field(default=None, max_length=512)
    trino_catalog: str | None = Field(default=None, max_length=255)
    trino_schema: str | None = Field(default=None, max_length=255)
    trino_http_scheme: str | None = Field(default=None, pattern='^(http|https)$')

    @model_validator(mode='before')
    @classmethod
    def normalize(cls, data: object) -> object:
        return _normalize_trino_settings(data)


class TrinoSettingsRead(TrinoSettings):
    model_config = ConfigDict(from_attributes=True)
