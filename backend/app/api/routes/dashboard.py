from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.models.assignment import PilotEmployeeAssignment
from app.models.employee import Employee
from app.models.pilot import Pilot
from app.models.pilot_weekly_metric import PilotWeeklyMetric
from app.schemas.dashboard import (
    CrossAssignmentItem,
    DashboardPilotAllocation,
    DashboardProfitabilityItem,
    DashboardSummary,
    ResourceByRcItem,
    ResourceLoadItem,
    WeeklyCostPoint,
)
from app.utils.week import to_week_start

router = APIRouter(prefix='/dashboard')


def _resolve_period(
    *,
    week_start_date: date | None = None,
    start_week: date | None = None,
    end_week: date | None = None,
) -> tuple[date, date, int]:
    if start_week is not None or end_week is not None:
        start = to_week_start(start_week or end_week or date.today())
        end = to_week_start(end_week or start_week or date.today())
    else:
        selected_week = to_week_start(week_start_date or date.today())
        start = selected_week
        end = selected_week

    if start > end:
        start, end = end, start

    weeks_count = ((end - start).days // 7) + 1
    return start, end, weeks_count


def _employee_weekly_load_map(db: Session, start_week: date, end_week: date) -> dict[int, list[Decimal]]:
    rows = db.execute(
        select(
            PilotEmployeeAssignment.employee_id,
            PilotEmployeeAssignment.week_start_date,
            func.coalesce(func.sum(PilotEmployeeAssignment.load_percent), 0),
        )
        .join(Pilot, Pilot.id == PilotEmployeeAssignment.pilot_id)
        .where(
            and_(
                PilotEmployeeAssignment.week_start_date >= start_week,
                PilotEmployeeAssignment.week_start_date <= end_week,
                Pilot.is_active.is_(True),
            )
        )
        .group_by(PilotEmployeeAssignment.employee_id, PilotEmployeeAssignment.week_start_date)
    ).all()

    grouped: dict[int, list[Decimal]] = defaultdict(list)
    for employee_id, _week_start, total_load in rows:
        grouped[employee_id].append(Decimal(str(total_load)))
    return grouped


@router.get('/summary', response_model=DashboardSummary)
def dashboard_summary(
    week_start_date: date | None = Query(default=None),
    start_week: date | None = Query(default=None),
    end_week: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    period_start, period_end, weeks_count = _resolve_period(
        week_start_date=week_start_date,
        start_week=start_week,
        end_week=end_week,
    )

    active_pilots_count = db.scalar(select(func.count()).select_from(Pilot).where(Pilot.is_active.is_(True))) or 0

    totals_row = db.execute(
        select(
            func.coalesce(func.sum(PilotWeeklyMetric.total_cost), 0),
            func.coalesce(func.sum(PilotWeeklyMetric.total_pshe), 0),
        )
        .join(Pilot, Pilot.id == PilotWeeklyMetric.pilot_id)
        .where(
            and_(
                PilotWeeklyMetric.week_start_date >= period_start,
                PilotWeeklyMetric.week_start_date <= period_end,
                Pilot.is_active.is_(True),
            )
        )
    ).one()

    total_cost = totals_row[0]
    total_pshe = totals_row[1]

    active_employees_count = (
        db.scalar(
            select(func.count(distinct(PilotEmployeeAssignment.employee_id)))
            .join(Pilot, Pilot.id == PilotEmployeeAssignment.pilot_id)
            .where(
                and_(
                    PilotEmployeeAssignment.week_start_date >= period_start,
                    PilotEmployeeAssignment.week_start_date <= period_end,
                    Pilot.is_active.is_(True),
                )
            )
        )
        or 0
    )

    metrics_rows = db.execute(
        select(
            Pilot.id,
            Pilot.name,
            Pilot.annual_revenue,
            func.coalesce(func.sum(PilotWeeklyMetric.total_hours), 0),
            func.coalesce(func.sum(PilotWeeklyMetric.total_pshe), 0),
            func.coalesce(func.sum(PilotWeeklyMetric.total_cost), 0),
        )
        .join(PilotWeeklyMetric, PilotWeeklyMetric.pilot_id == Pilot.id)
        .where(
            and_(
                PilotWeeklyMetric.week_start_date >= period_start,
                PilotWeeklyMetric.week_start_date <= period_end,
                Pilot.is_active.is_(True),
            )
        )
        .group_by(Pilot.id, Pilot.name, Pilot.annual_revenue)
    ).all()

    employees_per_pilot_rows = db.execute(
        select(
            PilotEmployeeAssignment.pilot_id,
            func.count(distinct(PilotEmployeeAssignment.employee_id)),
        )
        .join(Pilot, Pilot.id == PilotEmployeeAssignment.pilot_id)
        .where(
            and_(
                PilotEmployeeAssignment.week_start_date >= period_start,
                PilotEmployeeAssignment.week_start_date <= period_end,
                Pilot.is_active.is_(True),
            )
        )
        .group_by(PilotEmployeeAssignment.pilot_id)
    ).all()
    employees_per_pilot = {row[0]: row[1] for row in employees_per_pilot_rows}

    total_cost_decimal = Decimal(str(total_cost))
    resource_allocation: list[DashboardPilotAllocation] = []
    profitability_items: list[DashboardProfitabilityItem] = []

    for row in metrics_rows:
        pilot_id, pilot_name, annual_revenue_row, total_hours_row, total_pshe_row, total_cost_row = row

        pilot_total_cost = Decimal(str(total_cost_row))
        annual_revenue = Decimal(str(annual_revenue_row))
        period_revenue = (annual_revenue / Decimal('52')) * Decimal(str(weeks_count))
        profitability = period_revenue - pilot_total_cost
        cost_share = (
            (pilot_total_cost / total_cost_decimal) * Decimal('100')
            if total_cost_decimal > 0
            else Decimal('0')
        )
        margin_percent = (
            (profitability / period_revenue) * Decimal('100')
            if period_revenue > 0
            else Decimal('0')
        )

        resource_allocation.append(
            DashboardPilotAllocation(
                pilot_id=pilot_id,
                pilot_name=pilot_name,
                total_hours=total_hours_row,
                total_pshe=total_pshe_row,
                total_cost=total_cost_row,
                employees_count=employees_per_pilot.get(pilot_id, 0),
                cost_share_percent=cost_share,
            )
        )
        profitability_items.append(
            DashboardProfitabilityItem(
                pilot_id=pilot_id,
                pilot_name=pilot_name,
                revenue_estimate=period_revenue,
                total_cost=total_cost_row,
                profitability_estimate=profitability,
                margin_percent=margin_percent,
            )
        )

    resource_allocation.sort(key=lambda item: item.total_cost, reverse=True)
    profitability_items.sort(key=lambda item: item.profitability_estimate)

    return DashboardSummary(
        period_start_date=period_start,
        period_end_date=period_end,
        weeks_count=weeks_count,
        active_pilots_count=active_pilots_count,
        total_cost=total_cost,
        total_pshe=total_pshe,
        active_employees_count=active_employees_count,
        resource_allocation=resource_allocation[:10],
        worst_profitability_pilots=profitability_items[:5],
    )


@router.get('/cross-assignments', response_model=list[CrossAssignmentItem])
def cross_assignments(
    week_start_date: date | None = Query(default=None),
    start_week: date | None = Query(default=None),
    end_week: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CrossAssignmentItem]:
    period_start, period_end, _ = _resolve_period(
        week_start_date=week_start_date,
        start_week=start_week,
        end_week=end_week,
    )

    rows = db.execute(
        select(
            Employee.id,
            Employee.cas,
            Employee.full_name,
            Employee.rc,
            Pilot.name,
        )
        .join(PilotEmployeeAssignment, PilotEmployeeAssignment.employee_id == Employee.id)
        .join(Pilot, Pilot.id == PilotEmployeeAssignment.pilot_id)
        .where(
            and_(
                PilotEmployeeAssignment.week_start_date >= period_start,
                PilotEmployeeAssignment.week_start_date <= period_end,
                Pilot.is_active.is_(True),
            )
        )
        .order_by(Employee.full_name, Pilot.name)
    ).all()

    weekly_load_map = _employee_weekly_load_map(db, period_start, period_end)

    grouped: dict[int, dict[str, object]] = {}
    for employee_id, cas, full_name, rc, pilot_name in rows:
        if employee_id not in grouped:
            grouped[employee_id] = {
                'employee_id': employee_id,
                'cas': cas,
                'full_name': full_name,
                'rc': rc,
                'pilots': set(),
            }

        pilots = grouped[employee_id]['pilots']
        assert isinstance(pilots, set)
        pilots.add(pilot_name)

    output: list[CrossAssignmentItem] = []
    for payload in grouped.values():
        pilots_set = payload['pilots']
        assert isinstance(pilots_set, set)
        pilots = sorted(pilots_set)
        if len(pilots) < 2:
            continue

        employee_id = int(payload['employee_id'])
        week_loads = weekly_load_map.get(employee_id, [])
        average_load_percent = (
            sum(week_loads, start=Decimal('0')) / Decimal(str(len(week_loads)))
            if week_loads
            else Decimal('0')
        )
        overloaded = any(item > Decimal('100') for item in week_loads)

        output.append(
            CrossAssignmentItem(
                employee_id=employee_id,
                cas=payload['cas'],
                full_name=payload['full_name'],
                rc=payload['rc'],
                pilot_count=len(pilots),
                pilots=pilots,
                total_load_percent=average_load_percent,
                overloaded=overloaded,
            )
        )

    output.sort(key=lambda item: (item.overloaded, item.pilot_count, item.total_load_percent), reverse=True)
    return output


@router.get('/weekly-costs', response_model=list[WeeklyCostPoint])
def weekly_costs(
    weeks: int = Query(default=12, ge=1, le=104),
    start_week: date | None = Query(default=None),
    end_week: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[WeeklyCostPoint]:
    stmt = (
        select(
            PilotWeeklyMetric.week_start_date,
            func.coalesce(func.sum(PilotWeeklyMetric.total_cost), 0),
            func.coalesce(func.sum(PilotWeeklyMetric.total_pshe), 0),
        )
        .join(Pilot, Pilot.id == PilotWeeklyMetric.pilot_id)
        .where(Pilot.is_active.is_(True))
    )

    if start_week is not None or end_week is not None:
        period_start, period_end, _ = _resolve_period(start_week=start_week, end_week=end_week)
        stmt = stmt.where(
            and_(
                PilotWeeklyMetric.week_start_date >= period_start,
                PilotWeeklyMetric.week_start_date <= period_end,
            )
        )
        rows = db.execute(
            stmt.group_by(PilotWeeklyMetric.week_start_date).order_by(PilotWeeklyMetric.week_start_date)
        ).all()
        return [WeeklyCostPoint(week_start_date=row[0], total_cost=row[1], total_pshe=row[2]) for row in rows]

    rows = db.execute(
        stmt.group_by(PilotWeeklyMetric.week_start_date)
        .order_by(PilotWeeklyMetric.week_start_date.desc())
        .limit(weeks)
    ).all()

    return [
        WeeklyCostPoint(week_start_date=row[0], total_cost=row[1], total_pshe=row[2])
        for row in reversed(rows)
    ]


@router.get('/resource-load', response_model=list[ResourceLoadItem])
def resource_load(
    week_start_date: date | None = Query(default=None),
    start_week: date | None = Query(default=None),
    end_week: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ResourceLoadItem]:
    period_start, period_end, _ = _resolve_period(
        week_start_date=week_start_date,
        start_week=start_week,
        end_week=end_week,
    )

    hours_rows = db.execute(
        select(
            Employee.id,
            Employee.full_name,
            Employee.cas,
            func.coalesce(func.sum(PilotEmployeeAssignment.hours), 0),
        )
        .join(PilotEmployeeAssignment, PilotEmployeeAssignment.employee_id == Employee.id)
        .join(Pilot, Pilot.id == PilotEmployeeAssignment.pilot_id)
        .where(
            and_(
                PilotEmployeeAssignment.week_start_date >= period_start,
                PilotEmployeeAssignment.week_start_date <= period_end,
                Pilot.is_active.is_(True),
            )
        )
        .group_by(Employee.id, Employee.full_name, Employee.cas)
    ).all()

    weekly_load_map = _employee_weekly_load_map(db, period_start, period_end)

    result: list[ResourceLoadItem] = []
    for employee_id, full_name, cas, total_hours in hours_rows:
        week_loads = weekly_load_map.get(employee_id, [])
        average_load_percent = (
            sum(week_loads, start=Decimal('0')) / Decimal(str(len(week_loads)))
            if week_loads
            else Decimal('0')
        )
        overloaded = any(item > Decimal('100') for item in week_loads)

        result.append(
            ResourceLoadItem(
                employee_id=employee_id,
                full_name=full_name,
                cas=cas,
                total_load_percent=average_load_percent,
                total_hours=total_hours,
                overloaded=overloaded,
            )
        )

    result.sort(key=lambda item: item.total_load_percent, reverse=True)
    return result


@router.get('/resource-by-rc', response_model=list[ResourceByRcItem])
def resource_by_rc(
    week_start_date: date | None = Query(default=None),
    start_week: date | None = Query(default=None),
    end_week: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ResourceByRcItem]:
    period_start, period_end, _ = _resolve_period(
        week_start_date=week_start_date,
        start_week=start_week,
        end_week=end_week,
    )

    rows = db.execute(
        select(
            Employee.rc,
            func.count(distinct(Employee.id)),
            func.count(distinct(PilotEmployeeAssignment.pilot_id)),
            func.coalesce(func.sum(PilotEmployeeAssignment.hours), 0),
            func.coalesce(func.sum(PilotEmployeeAssignment.pshe), 0),
        )
        .join(PilotEmployeeAssignment, PilotEmployeeAssignment.employee_id == Employee.id)
        .join(Pilot, Pilot.id == PilotEmployeeAssignment.pilot_id)
        .where(
            and_(
                PilotEmployeeAssignment.week_start_date >= period_start,
                PilotEmployeeAssignment.week_start_date <= period_end,
                Pilot.is_active.is_(True),
            )
        )
        .group_by(Employee.rc)
        .order_by(func.sum(PilotEmployeeAssignment.hours).desc())
    ).all()

    total_hours = sum(Decimal(str(row[3])) for row in rows)

    result: list[ResourceByRcItem] = []
    for row in rows:
        rc, employees_count, pilots_count, rc_hours, rc_pshe = row
        rc_hours_decimal = Decimal(str(rc_hours))
        share_percent = (
            (rc_hours_decimal / total_hours) * Decimal('100')
            if total_hours > 0
            else Decimal('0')
        )

        result.append(
            ResourceByRcItem(
                rc=rc,
                employees_count=employees_count,
                pilots_count=pilots_count,
                total_hours=rc_hours,
                total_pshe=rc_pshe,
                load_share_percent=share_percent,
            )
        )

    return result
