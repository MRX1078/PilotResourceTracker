from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.app_settings import TrinoSettings, TrinoSettingsRead
from app.services.app_settings_service import AppSettingsService

router = APIRouter(prefix='/system/settings')


@router.get('/trino', response_model=TrinoSettingsRead)
def get_trino_settings(db: Session = Depends(get_db)) -> TrinoSettingsRead:
    instance = AppSettingsService(db).get()
    return TrinoSettingsRead.model_validate(instance)


@router.put('/trino', response_model=TrinoSettingsRead)
def update_trino_settings(
    payload: TrinoSettings,
    db: Session = Depends(get_db),
) -> TrinoSettingsRead:
    instance = AppSettingsService(db).update_trino_settings(payload)
    return TrinoSettingsRead.model_validate(instance)
