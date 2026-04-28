from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class EmployeeBase(BaseModel):
    cas: str | None = None
    full_name: str
    rc: str


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class EmployeePilotLoad(BaseModel):
    pilot_id: int
    pilot_name: str
    week_start_date: date
    load_percent: Decimal
    hours: Decimal
    pshe: Decimal


class EmployeeWeeklyLoad(BaseModel):
    week_start_date: date
    total_load_percent: Decimal
    total_hours: Decimal


class EmployeeDetail(EmployeeRead):
    pilots: list[EmployeePilotLoad] = []
    weekly_loads: list[EmployeeWeeklyLoad] = []
    selected_week_total_load_percent: Decimal = Decimal('0')
    is_overloaded: bool = False


class EmployeeCsvImportError(BaseModel):
    row_number: int
    error: str


class EmployeeCsvImportResponse(BaseModel):
    total_rows: int
    imported_count: int
    created_count: int
    updated_count: int
    errors: list[EmployeeCsvImportError] = []
