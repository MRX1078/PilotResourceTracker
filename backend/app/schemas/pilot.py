from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AccountingMode


class PilotBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    annual_revenue: Decimal = Decimal('0')
    accounting_mode: AccountingMode = AccountingMode.MANUAL
    sql_query: str | None = None
    additional_pshe_default: Decimal = Decimal('0')
    is_active: bool = True


class PilotCreate(PilotBase):
    pass


class PilotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    annual_revenue: Decimal | None = None
    accounting_mode: AccountingMode | None = None
    sql_query: str | None = None
    additional_pshe_default: Decimal | None = None
    is_active: bool | None = None


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


class PilotSqlValidationResponse(BaseModel):
    is_valid: bool
    columns: list[str] = []
    message: str
