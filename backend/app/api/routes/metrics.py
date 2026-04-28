from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models.pilot import Pilot
from app.models.pilot_weekly_metric import PilotWeeklyMetric
from app.schemas.metric import PilotWeeklyMetricRead
from app.utils.week import to_week_start

router = APIRouter(prefix='/pilots')


@router.get('/{pilot_id}/metrics', response_model=list[PilotWeeklyMetricRead])
def get_pilot_metrics(
    pilot_id: int,
    start_week: date | None = Query(default=None),
    end_week: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PilotWeeklyMetricRead]:
    pilot = db.get(Pilot, pilot_id)
    if not pilot or not pilot.is_active:
        raise HTTPException(status_code=404, detail='Pilot not found')

    stmt = select(PilotWeeklyMetric).where(PilotWeeklyMetric.pilot_id == pilot_id)

    if start_week:
        stmt = stmt.where(PilotWeeklyMetric.week_start_date >= to_week_start(start_week))
    if end_week:
        stmt = stmt.where(PilotWeeklyMetric.week_start_date <= to_week_start(end_week))

    stmt = stmt.order_by(PilotWeeklyMetric.week_start_date)

    return list(db.scalars(stmt).all())
