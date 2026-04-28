from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PilotWeeklyMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pilot_id: int
    week_start_date: date
    total_hours: Decimal
    total_pshe: Decimal
    additional_pshe: Decimal
    total_cost: Decimal
    annual_revenue: Decimal
    weekly_revenue_estimate: Decimal
    profitability_estimate: Decimal
    created_at: datetime
    updated_at: datetime
