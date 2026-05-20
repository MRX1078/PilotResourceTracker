from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.models.enums import AccountingMode, QueryRunStatus
from app.models.pilot import Pilot
from app.models.trino_query_run import TrinoQueryRun
from app.schemas.trino_run import PilotLatestRun, TrinoRunRead

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


@router.get('/latest-by-pilot', response_model=list[PilotLatestRun])
def list_latest_runs_by_pilot(db: Session = Depends(get_db)) -> list[PilotLatestRun]:
    """One entry per active SQL-mode pilot: the most recent run + a flag
    indicating whether the pilot has *ever* had a successful run.

    The Updates page uses this to show only the current state per pilot and
    to decide which pilots are eligible for the batch refresh button (only
    those with at least one prior successful run).
    """

    pilots = db.scalars(
        select(Pilot)
        .where(Pilot.is_active.is_(True))
        .where(Pilot.accounting_mode == AccountingMode.SQL)
        .order_by(Pilot.name.asc())
    ).all()

    result: list[PilotLatestRun] = []
    for pilot in pilots:
        last_run = db.scalar(
            select(TrinoQueryRun)
            .where(TrinoQueryRun.pilot_id == pilot.id)
            .order_by(TrinoQueryRun.started_at.desc())
        )

        has_successful_run = db.scalar(
            select(
                exists().where(
                    TrinoQueryRun.pilot_id == pilot.id,
                    TrinoQueryRun.status == QueryRunStatus.SUCCESS,
                )
            )
        ) or False

        last_run_payload: TrinoRunRead | None = None
        if last_run is not None:
            last_run_payload = TrinoRunRead(
                id=last_run.id,
                pilot_id=last_run.pilot_id,
                pilot_name=pilot.name,
                started_at=last_run.started_at,
                finished_at=last_run.finished_at,
                status=last_run.status,
                error_message=last_run.error_message,
                rows_returned=last_run.rows_returned,
            )

        result.append(
            PilotLatestRun(
                pilot_id=pilot.id,
                pilot_name=pilot.name,
                has_successful_run=bool(has_successful_run),
                last_run=last_run_payload,
            )
        )

    return result
