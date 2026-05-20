from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSettings(Base):
    """Singleton table that holds global application settings.

    All rows here use a fixed primary key (id=1). The Trino connection fields
    used to live on each pilot, but are now configured once on the Backup page
    and reused by every SQL-mode pilot.
    """

    __tablename__ = 'app_settings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    trino_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trino_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trino_user: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trino_password: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    trino_catalog: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trino_schema: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trino_http_scheme: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
