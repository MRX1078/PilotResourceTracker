from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.backup import BackupImportResponse
from app.services.backup_service import BackupService, BackupValidationError

router = APIRouter(prefix='/system/backup')


@router.get('/export')
def export_backup(db: Session = Depends(get_db)) -> Response:
    service = BackupService(db)
    backup_bytes = service.export_snapshot_json_bytes()
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f'pilot_tracker_backup_{timestamp}.json'

    return Response(
        content=backup_bytes,
        media_type='application/json',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post('/import', response_model=BackupImportResponse)
async def import_backup(
    file: UploadFile = File(...),
    run_refresh_all_sql: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> BackupImportResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail='Backup file is empty')

    try:
        snapshot = json.loads(raw.decode('utf-8-sig'))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Invalid backup JSON: {exc}') from exc

    service = BackupService(db)
    try:
        return service.import_snapshot(snapshot, run_refresh_all_sql=run_refresh_all_sql)
    except BackupValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
