from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import QueryRunStatus


class TrinoRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pilot_id: int
    pilot_name: str
    started_at: datetime
    finished_at: datetime | None
    status: QueryRunStatus
    error_message: str | None
    rows_returned: int
