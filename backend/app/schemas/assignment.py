from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import AssignmentSource


class AssignmentBase(BaseModel):
    employee_id: int | None = None
    week_start_date: date
    load_percent: Decimal | None = None
    pshe: Decimal | None = None
    hours: Decimal | None = None
    source: AssignmentSource = AssignmentSource.MANUAL

    @model_validator(mode='after')
    def validate_capacity_fields(self):
        if self.load_percent is None and self.pshe is None and self.hours is None:
            raise ValueError('At least one of hours, pshe or load_percent should be provided')
        return self


class AssignmentCreate(AssignmentBase):
    cas: str | None = None
    full_name: str | None = None
    rc: str | None = None


class AssignmentUpdate(BaseModel):
    week_start_date: date | None = None
    load_percent: Decimal | None = None
    pshe: Decimal | None = None
    hours: Decimal | None = None

    @model_validator(mode='after')
    def validate_capacity_fields(self):
        if self.load_percent is None and self.pshe is None and self.hours is None and self.week_start_date is None:
            raise ValueError('Nothing to update')
        return self


class AssignmentEmployeeInfo(BaseModel):
    id: int
    cas: str | None
    full_name: str
    rc: str


class OtherPilotInfo(BaseModel):
    pilot_id: int
    pilot_name: str


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pilot_id: int
    employee_id: int
    week_start_date: date
    load_percent: Decimal
    pshe: Decimal
    hours: Decimal
    source: AssignmentSource
    created_at: datetime
    updated_at: datetime
    employee: AssignmentEmployeeInfo
    other_pilots: list[OtherPilotInfo] = []


class AssignmentCsvImportError(BaseModel):
    row_number: int
    error: str


class AssignmentCsvImportResponse(BaseModel):
    total_rows: int
    imported_count: int
    created_count: int
    updated_count: int
    weeks_affected: list[date]
    errors: list[AssignmentCsvImportError] = []
