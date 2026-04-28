from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.models.assignment import PilotEmployeeAssignment
from app.models.enums import AccountingMode
from app.models.pilot import Pilot
from app.models.pilot_weekly_metric import PilotWeeklyMetric
from app.models.trino_query_run import TrinoQueryRun
from app.schemas.pilot import (
    PilotCreate,
    PilotListItem,
    PilotMetricSnapshot,
    PilotRead,
    PilotSqlValidationRequest,
    PilotSqlValidationResponse,
    PilotUpdate,
)
from app.services.refresh_service import RefreshService
from app.services.trino_service import TrinoConnectionOptions

router = APIRouter(prefix='/pilots')


@router.get('', response_model=list[PilotListItem])
def list_pilots(db: Session = Depends(get_db)) -> list[PilotListItem]:
    pilots = db.scalars(select(Pilot).where(Pilot.is_active.is_(True)).order_by(Pilot.created_at.desc())).all()

    result: list[PilotListItem] = []
    for pilot in pilots:
        latest_metric = db.scalar(
            select(PilotWeeklyMetric)
            .where(PilotWeeklyMetric.pilot_id == pilot.id)
            .order_by(PilotWeeklyMetric.week_start_date.desc())
        )
        employee_count = db.scalar(
            select(func.count(distinct(PilotEmployeeAssignment.employee_id))).where(
                PilotEmployeeAssignment.pilot_id == pilot.id
            )
        )
        last_run = db.scalar(
            select(TrinoQueryRun)
            .where(TrinoQueryRun.pilot_id == pilot.id)
            .order_by(TrinoQueryRun.started_at.desc())
        )

        snapshot = None
        if latest_metric:
            snapshot = PilotMetricSnapshot(
                week_start_date=latest_metric.week_start_date,
                total_cost=latest_metric.total_cost,
                total_pshe=latest_metric.total_pshe,
            )

        result.append(
            PilotListItem(
                id=pilot.id,
                name=pilot.name,
                description=pilot.description,
                annual_revenue=pilot.annual_revenue,
                accounting_mode=pilot.accounting_mode,
                sql_query=pilot.sql_query,
                trino_host=pilot.trino_host,
                trino_port=pilot.trino_port,
                trino_user=pilot.trino_user,
                trino_password=None,
                trino_catalog=pilot.trino_catalog,
                trino_schema=pilot.trino_schema,
                trino_http_scheme=pilot.trino_http_scheme,
                additional_pshe_default=pilot.additional_pshe_default,
                is_active=pilot.is_active,
                created_at=pilot.created_at,
                updated_at=pilot.updated_at,
                latest_metric=snapshot,
                employees_count=employee_count or 0,
                last_refresh_status=last_run.status.value if last_run else None,
                last_refresh_started_at=last_run.started_at if last_run else None,
            )
        )

    return result


@router.get('/refresh-all')
def refresh_all_wrong_method_hint() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail='Use POST /api/pilots/refresh-all to refresh SQL pilots',
    )


@router.post('/refresh-all')
def refresh_all_sql_pilots(db: Session = Depends(get_db)):
    refresh_service = RefreshService(db)
    return refresh_service.refresh_all_sql_pilots()


@router.post('/validate-sql', response_model=PilotSqlValidationResponse)
def validate_sql_query(payload: PilotSqlValidationRequest, db: Session = Depends(get_db)):
    refresh_service = RefreshService(db)
    connection_options = TrinoConnectionOptions(
        host=payload.trino_host,
        port=payload.trino_port,
        user=payload.trino_user,
        password=payload.trino_password,
        catalog=payload.trino_catalog,
        schema=payload.trino_schema,
        http_scheme=payload.trino_http_scheme,
    )
    has_overrides = any(
        (
            connection_options.host,
            connection_options.port is not None,
            connection_options.user,
            connection_options.password,
            connection_options.catalog,
            connection_options.schema,
            connection_options.http_scheme,
        )
    )
    is_valid, columns, message = refresh_service.validate_sql_query(
        payload.sql_query,
        connection_options=connection_options if has_overrides else None,
    )
    return PilotSqlValidationResponse(is_valid=is_valid, columns=columns, message=message)


@router.post('', response_model=PilotRead, status_code=status.HTTP_201_CREATED)
def create_pilot(payload: PilotCreate, db: Session = Depends(get_db)) -> PilotRead:
    if payload.accounting_mode == AccountingMode.SQL and not payload.sql_query:
        raise HTTPException(status_code=400, detail='sql_query is required for sql accounting mode')

    pilot = Pilot(**payload.model_dump())
    db.add(pilot)
    db.commit()
    db.refresh(pilot)
    return pilot


@router.get('/{pilot_id}', response_model=PilotRead)
def get_pilot(pilot_id: int, db: Session = Depends(get_db)) -> PilotRead:
    pilot = db.get(Pilot, pilot_id)
    if not pilot or not pilot.is_active:
        raise HTTPException(status_code=404, detail='Pilot not found')
    return pilot


@router.put('/{pilot_id}', response_model=PilotRead)
def update_pilot(pilot_id: int, payload: PilotUpdate, db: Session = Depends(get_db)) -> PilotRead:
    pilot = db.get(Pilot, pilot_id)
    if not pilot or not pilot.is_active:
        raise HTTPException(status_code=404, detail='Pilot not found')

    updates = payload.model_dump(exclude_unset=True)

    next_mode = updates.get('accounting_mode', pilot.accounting_mode)
    next_query = updates.get('sql_query', pilot.sql_query)

    if next_mode == AccountingMode.SQL and not next_query:
        raise HTTPException(status_code=400, detail='sql_query is required for sql accounting mode')

    for field, value in updates.items():
        setattr(pilot, field, value)

    db.commit()
    db.refresh(pilot)
    return pilot


@router.delete('/{pilot_id}')
def delete_pilot(pilot_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    pilot = db.get(Pilot, pilot_id)
    if not pilot or not pilot.is_active:
        raise HTTPException(status_code=404, detail='Pilot not found')

    pilot.is_active = False
    db.commit()
    return {'message': 'Pilot deactivated'}


@router.post('/{pilot_id}/refresh')
def refresh_single_pilot(pilot_id: int, db: Session = Depends(get_db)):
    refresh_service = RefreshService(db)
    try:
        return refresh_service.refresh_single_pilot(pilot_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Refresh failed: {exc}') from exc
