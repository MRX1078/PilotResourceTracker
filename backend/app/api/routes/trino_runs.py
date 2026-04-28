from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.models.pilot import Pilot
from app.models.trino_query_run import TrinoQueryRun
from app.schemas.trino_run import TrinoRunRead

router = APIRouter(prefix='/trino-runs')


@router.get('', response_model=list[TrinoRunRead])
def list_trino_runs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[TrinoRunRead]:
    rows = db.execute(
        select(TrinoQueryRun, Pilot.name)
        .join(Pilot, Pilot.id == TrinoQueryRun.pilot_id)
        .order_by(TrinoQueryRun.started_at.desc())
        .limit(limit)
    ).all()

    return [
        TrinoRunRead(
            id=row[0].id,
            pilot_id=row[0].pilot_id,
            pilot_name=row[1],
            started_at=row[0].started_at,
            finished_at=row[0].finished_at,
            status=row[0].status,
            error_message=row[0].error_message,
            rows_returned=row[0].rows_returned,
        )
        for row in rows
    ]
