from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardTopPilot(BaseModel):
    pilot_id: int
    pilot_name: str
    total_cost: Decimal
    total_pshe: Decimal


class DashboardPilotAllocation(BaseModel):
    pilot_id: int
    pilot_name: str
    total_hours: Decimal
    total_pshe: Decimal
    total_cost: Decimal
    employees_count: int
    cost_share_percent: Decimal


class DashboardProfitabilityItem(BaseModel):
    pilot_id: int
    pilot_name: str
    revenue_estimate: Decimal
    total_cost: Decimal
    profitability_estimate: Decimal
    margin_percent: Decimal


class DashboardSummary(BaseModel):
    period_start_date: date
    period_end_date: date
    weeks_count: int
    active_pilots_count: int
    total_cost: Decimal
    total_pshe: Decimal
    active_employees_count: int
    resource_allocation: list[DashboardPilotAllocation]
    worst_profitability_pilots: list[DashboardProfitabilityItem]


class CrossAssignmentItem(BaseModel):
    employee_id: int
    cas: str | None
    full_name: str
    rc: str
    pilot_count: int
    pilots: list[str]
    total_load_percent: Decimal
    overloaded: bool


class WeeklyCostPoint(BaseModel):
    week_start_date: date
    total_cost: Decimal
    total_pshe: Decimal


class ResourceLoadItem(BaseModel):
    employee_id: int
    full_name: str
    cas: str | None
    total_load_percent: Decimal
    total_hours: Decimal
    overloaded: bool


class ResourceByRcItem(BaseModel):
    rc: str
    employees_count: int
    pilots_count: int
    total_hours: Decimal
    total_pshe: Decimal
    load_share_percent: Decimal
