from __future__ import annotations

from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AccountingMode


class Pilot(Base):
    __tablename__ = 'pilots'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    annual_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    accounting_mode: Mapped[AccountingMode] = mapped_column(
        Enum(AccountingMode, name='accounting_mode_enum'),
        nullable=False,
        default=AccountingMode.MANUAL,
    )
    sql_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trino_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trino_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trino_user: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trino_password: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    trino_catalog: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trino_schema: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trino_http_scheme: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    additional_pshe_default: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    assignments = relationship('PilotEmployeeAssignment', back_populates='pilot', cascade='all, delete-orphan')
    weekly_metrics = relationship('PilotWeeklyMetric', back_populates='pilot', cascade='all, delete-orphan')
    query_runs = relationship('TrinoQueryRun', back_populates='pilot', cascade='all, delete-orphan')
