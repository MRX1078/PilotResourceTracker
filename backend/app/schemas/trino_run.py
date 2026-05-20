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


class PilotLatestRun(BaseModel):
    """Latest known refresh state for a SQL pilot — used by the Updates page."""

    pilot_id: int
    pilot_name: str
    has_successful_run: bool
    last_run: TrinoRunRead | None = None
