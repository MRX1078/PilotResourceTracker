from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Employee(Base):
    __tablename__ = 'employees'
    __table_args__ = (
        UniqueConstraint('full_name', 'rc', name='uq_employees_full_name_rc'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cas: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rc: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    assignments = relationship('PilotEmployeeAssignment', back_populates='employee', cascade='all, delete-orphan')
