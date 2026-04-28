from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import QueryRunStatus


class TrinoQueryRun(Base):
    __tablename__ = 'trino_query_runs'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pilot_id: Mapped[int] = mapped_column(ForeignKey('pilots.id', ondelete='CASCADE'), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[QueryRunStatus] = mapped_column(
        Enum(QueryRunStatus, name='query_run_status_enum'),
        nullable=False,
        default=QueryRunStatus.PENDING,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rows_returned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pilot = relationship('Pilot', back_populates='query_runs')
