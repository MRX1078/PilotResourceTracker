from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AccountingMode


def _normalize_optional_trino_fields(data: object) -> object:
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


class PilotBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    annual_revenue: Decimal = Decimal('0')
    accounting_mode: AccountingMode = AccountingMode.MANUAL
    sql_query: str | None = None
    trino_host: str | None = Field(default=None, max_length=255)
    trino_port: int | None = Field(default=None, ge=1, le=65535)
    trino_user: str | None = Field(default=None, max_length=255)
    trino_password: str | None = Field(default=None, max_length=512)
    trino_catalog: str | None = Field(default=None, max_length=255)
    trino_schema: str | None = Field(default=None, max_length=255)
    trino_http_scheme: str | None = Field(default=None, pattern='^(http|https)$')
    additional_pshe_default: Decimal = Decimal('0')
    is_active: bool = True

    @model_validator(mode='before')
    @classmethod
    def normalize_trino_fields(cls, data: object) -> object:
        return _normalize_optional_trino_fields(data)


class PilotCreate(PilotBase):
    pass


class PilotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    annual_revenue: Decimal | None = None
    accounting_mode: AccountingMode | None = None
    sql_query: str | None = None
    trino_host: str | None = Field(default=None, max_length=255)
    trino_port: int | None = Field(default=None, ge=1, le=65535)
    trino_user: str | None = Field(default=None, max_length=255)
    trino_password: str | None = Field(default=None, max_length=512)
    trino_catalog: str | None = Field(default=None, max_length=255)
    trino_schema: str | None = Field(default=None, max_length=255)
    trino_http_scheme: str | None = Field(default=None, pattern='^(http|https)$')
    additional_pshe_default: Decimal | None = None
    is_active: bool | None = None

    @model_validator(mode='before')
    @classmethod
    def normalize_trino_fields(cls, data: object) -> object:
        return _normalize_optional_trino_fields(data)


class PilotMetricSnapshot(BaseModel):
    week_start_date: date
    total_cost: Decimal
    total_pshe: Decimal


class PilotRead(PilotBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PilotListItem(PilotRead):
    latest_metric: PilotMetricSnapshot | None = None
    employees_count: int = 0
    last_refresh_status: str | None = None
    last_refresh_started_at: datetime | None = None


class PilotSqlValidationRequest(BaseModel):
    sql_query: str = Field(min_length=1)
    trino_host: str | None = Field(default=None, max_length=255)
    trino_port: int | None = Field(default=None, ge=1, le=65535)
    trino_user: str | None = Field(default=None, max_length=255)
    trino_password: str | None = Field(default=None, max_length=512)
    trino_catalog: str | None = Field(default=None, max_length=255)
    trino_schema: str | None = Field(default=None, max_length=255)
    trino_http_scheme: str | None = Field(default=None, pattern='^(http|https)$')

    @model_validator(mode='before')
    @classmethod
    def normalize_trino_fields(cls, data: object) -> object:
        return _normalize_optional_trino_fields(data)


class PilotSqlValidationResponse(BaseModel):
    is_valid: bool
    columns: list[str] = []
    message: str
