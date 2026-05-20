from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings
from app.schemas.app_settings import TrinoSettings


class AppSettingsService:
    """Reads/writes the global app settings singleton row."""

    SETTINGS_ID = 1

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self) -> AppSettings:
        instance = self.session.get(AppSettings, self.SETTINGS_ID)
        if instance is None:
            instance = AppSettings(id=self.SETTINGS_ID)
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
        return instance

    def update_trino_settings(self, payload: TrinoSettings) -> AppSettings:
        instance = self.get()
        for field, value in payload.model_dump().items():
            setattr(instance, field, value)
        self.session.commit()
        self.session.refresh(instance)
        return instance
