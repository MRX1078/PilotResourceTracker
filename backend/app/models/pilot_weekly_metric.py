from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PilotWeeklyMetric(Base):
    __tablename__ = 'pilot_weekly_metrics'
    __table_args__ = (
        UniqueConstraint('pilot_id', 'week_start_date', name='uq_pilot_weekly_metrics_pilot_week'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pilot_id: Mapped[int] = mapped_column(ForeignKey('pilots.id', ondelete='CASCADE'), nullable=False, index=True)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_hours: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    total_pshe: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    additional_pshe: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    annual_revenue: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    weekly_revenue_estimate: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    profitability_estimate: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    pilot = relationship('Pilot', back_populates='weekly_metrics')
