from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.assignment import PilotEmployeeAssignment
from app.models.pilot import Pilot
from app.models.pilot_weekly_metric import PilotWeeklyMetric


def as_decimal(value: Decimal | float | int | str | None) -> Decimal:
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def derive_load_percent(hours: Decimal, work_hours_per_week: Decimal) -> Decimal:
    if work_hours_per_week == 0:
        return Decimal('0')
    return (hours / work_hours_per_week) * Decimal('100')


def derive_pshe(hours: Decimal, work_hours_per_week: Decimal) -> Decimal:
    if work_hours_per_week == 0:
        return Decimal('0')
    return hours / work_hours_per_week


def derive_hours(
    load_percent: Decimal | None,
    pshe: Decimal | None,
    work_hours_per_week: Decimal,
) -> Decimal:
    if pshe is not None:
        return pshe * work_hours_per_week
    if load_percent is not None:
        return (load_percent / Decimal('100')) * work_hours_per_week
    return Decimal('0')


def calculate_total_cost(
    total_hours: Decimal,
    total_pshe: Decimal,
    work_hours_per_week: Decimal,
    cost_per_minute: Decimal,
) -> Decimal:
    if total_hours > 0:
        return total_hours * Decimal('60') * cost_per_minute
    return total_pshe * work_hours_per_week * Decimal('60') * cost_per_minute


def normalize_assignment_values(
    hours: Decimal | None,
    pshe: Decimal | None,
    load_percent: Decimal | None,
    *,
    work_hours_per_week: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    dec_hours = as_decimal(hours) if hours is not None else None
    dec_pshe = as_decimal(pshe) if pshe is not None else None
    dec_load = as_decimal(load_percent) if load_percent is not None else None

    if dec_hours is None:
        dec_hours = derive_hours(dec_load, dec_pshe, work_hours_per_week)

    if dec_pshe is None:
        dec_pshe = derive_pshe(dec_hours, work_hours_per_week)

    if dec_load is None:
        dec_load = derive_load_percent(dec_hours, work_hours_per_week)

    return dec_hours, dec_pshe, dec_load


def _weekly_revenue(annual_revenue: Decimal) -> Decimal:
    return annual_revenue / Decimal('52')


def recompute_weekly_metric(session: Session, pilot_id: int, week_start_date: date) -> PilotWeeklyMetric:
    pilot = session.get(Pilot, pilot_id)
    if not pilot:
        raise ValueError(f'Pilot {pilot_id} not found')

    sums_stmt = select(
        func.coalesce(func.sum(PilotEmployeeAssignment.hours), 0),
        func.coalesce(func.sum(PilotEmployeeAssignment.pshe), 0),
    ).where(
        PilotEmployeeAssignment.pilot_id == pilot_id,
        PilotEmployeeAssignment.week_start_date == week_start_date,
    )

    total_hours_raw, total_pshe_raw = session.execute(sums_stmt).one()
    total_hours = as_decimal(total_hours_raw)
    total_pshe_without_additional = as_decimal(total_pshe_raw)
    additional_pshe = as_decimal(pilot.additional_pshe_default)
    total_pshe = total_pshe_without_additional + additional_pshe

    work_hours = as_decimal(settings.work_hours_per_week)
    cost_per_minute = as_decimal(settings.cost_per_minute)

    total_cost = calculate_total_cost(total_hours, total_pshe, work_hours, cost_per_minute)
    annual_revenue = as_decimal(pilot.annual_revenue)
    weekly_revenue_estimate = _weekly_revenue(annual_revenue)
    profitability_estimate = weekly_revenue_estimate - total_cost

    metric = session.scalar(
        select(PilotWeeklyMetric).where(
            PilotWeeklyMetric.pilot_id == pilot_id,
            PilotWeeklyMetric.week_start_date == week_start_date,
        )
    )

    if not metric:
        metric = PilotWeeklyMetric(
            pilot_id=pilot_id,
            week_start_date=week_start_date,
        )
        session.add(metric)

    metric.total_hours = total_hours
    metric.total_pshe = total_pshe
    metric.additional_pshe = additional_pshe
    metric.total_cost = total_cost
    metric.annual_revenue = annual_revenue
    metric.weekly_revenue_estimate = weekly_revenue_estimate
    metric.profitability_estimate = profitability_estimate

    session.flush()
    return metric


def recompute_pilot_metrics(session: Session, pilot_id: int, keep_empty_weeks: bool = False) -> None:
    week_rows = session.execute(
        select(PilotEmployeeAssignment.week_start_date)
        .where(PilotEmployeeAssignment.pilot_id == pilot_id)
        .distinct()
    ).all()

    weeks = [row[0] for row in week_rows]

    if not keep_empty_weeks:
        session.execute(
            delete(PilotWeeklyMetric).where(
                PilotWeeklyMetric.pilot_id == pilot_id,
                PilotWeeklyMetric.week_start_date.not_in(weeks) if weeks else True,
            )
        )

    if not weeks:
        return

    for week_start_date in weeks:
        recompute_weekly_metric(session, pilot_id, week_start_date)


def recompute_multiple_weeks(session: Session, pilot_id: int, weeks: Iterable[date]) -> None:
    unique_weeks = sorted(set(weeks))
    for week in unique_weeks:
        recompute_weekly_metric(session, pilot_id, week)
