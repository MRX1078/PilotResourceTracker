from decimal import Decimal

from app.services.metrics_service import (
    calculate_total_cost,
    derive_load_percent,
    derive_pshe,
    normalize_assignment_values,
)


def test_cost_prefers_hours_when_available() -> None:
    result = calculate_total_cost(
        total_hours=Decimal('10'),
        total_pshe=Decimal('999'),
        work_hours_per_week=Decimal('40'),
        cost_per_minute=Decimal('23'),
    )

    assert result == Decimal('13800')


def test_cost_uses_pshe_when_hours_is_zero() -> None:
    result = calculate_total_cost(
        total_hours=Decimal('0'),
        total_pshe=Decimal('1.5'),
        work_hours_per_week=Decimal('40'),
        cost_per_minute=Decimal('23'),
    )

    assert result == Decimal('82800')


def test_normalize_assignment_values_from_hours() -> None:
    hours, pshe, load_percent = normalize_assignment_values(
        hours=Decimal('20'),
        pshe=None,
        load_percent=None,
        work_hours_per_week=Decimal('40'),
    )

    assert hours == Decimal('20')
    assert pshe == Decimal('0.5')
    assert load_percent == Decimal('50')


def test_derive_helpers() -> None:
    assert derive_pshe(Decimal('16'), Decimal('40')) == Decimal('0.4')
    assert derive_load_percent(Decimal('16'), Decimal('40')) == Decimal('40')
