from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.refresh import RefreshAllResponse


class BackupSettings(BaseModel):
    work_hours_per_week: float
    cost_per_minute: float


class BackupCounts(BaseModel):
    pilots: int
    employees: int
    assignments: int
    metrics: int
    trino_query_runs: int


class BackupImportResponse(BaseModel):
    message: str
    imported_at: datetime
    imported: BackupCounts
    settings_from_backup: BackupSettings
    refresh_all_result: RefreshAllResponse | None = None
    warnings: list[str] = []
