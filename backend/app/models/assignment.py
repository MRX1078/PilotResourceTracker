from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AssignmentSource


class PilotEmployeeAssignment(Base):
    __tablename__ = 'pilot_employee_assignments'
    __table_args__ = (
        UniqueConstraint(
            'pilot_id',
            'employee_id',
            'week_start_date',
            'source',
            name='uq_pilot_employee_week_source',
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pilot_id: Mapped[int] = mapped_column(ForeignKey('pilots.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    load_percent: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    pshe: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    hours: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    source: Mapped[AssignmentSource] = mapped_column(
        Enum(AssignmentSource, name='assignment_source_enum'),
        nullable=False,
        default=AssignmentSource.MANUAL,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    pilot = relationship('Pilot', back_populates='assignments')
    employee = relationship('Employee', back_populates='assignments')
