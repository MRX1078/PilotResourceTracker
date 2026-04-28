from datetime import date
from decimal import Decimal

import pytest

from app.services.refresh_service import RefreshService, RefreshValidationError
from app.services.trino_service import TrinoQueryResult


def _service() -> RefreshService:
    return RefreshService(session=None)  # type: ignore[arg-type]


def test_validate_columns_allows_cas_only_identifier() -> None:
    result = TrinoQueryResult(columns=['week_start_date', 'cas', 'hours'], rows=[])
    _service()._validate_columns(result)


def test_validate_columns_allows_date_cas_hours_format() -> None:
    result = TrinoQueryResult(columns=['date', 'cas', 'hours'], rows=[])
    _service()._validate_columns(result)


def test_validate_columns_allows_full_name_rc_identifier() -> None:
    result = TrinoQueryResult(columns=['week_start_date', 'full_name', 'rc', 'hours'], rows=[])
    _service()._validate_columns(result)


def test_validate_columns_requires_week_or_date() -> None:
    result = TrinoQueryResult(columns=['cas', 'hours'], rows=[])
    with pytest.raises(RefreshValidationError, match='week_start_date'):
        _service()._validate_columns(result)


def test_validate_columns_requires_identifier_columns() -> None:
    result = TrinoQueryResult(columns=['week_start_date', 'hours'], rows=[])
    with pytest.raises(RefreshValidationError, match='employee identifier'):
        _service()._validate_columns(result)


def test_normalize_row_allows_cas_without_full_name_rc() -> None:
    row = {
        'week_start_date': date(2026, 4, 27),
        'cas': 'cas001',
        'hours': Decimal('10'),
    }

    normalized = _service()._normalize_row(row)

    assert normalized.week_start_date == date(2026, 4, 27)
    assert normalized.cas == 'cas001'
    assert normalized.full_name is None
    assert normalized.rc is None
    assert normalized.hours == Decimal('10')
    assert normalized.pshe == Decimal('0.25')
    assert normalized.load_percent == Decimal('25')


def test_normalize_row_accepts_date_column_and_converts_to_week_start() -> None:
    row = {
        'date': date(2026, 4, 30),
        'cas': 'cas001',
        'hours': Decimal('8'),
    }

    normalized = _service()._normalize_row(row)
    assert normalized.week_start_date == date(2026, 4, 27)
    assert normalized.hours == Decimal('8')


def test_normalize_row_requires_identity_per_row() -> None:
    row = {
        'week_start_date': date(2026, 4, 27),
        'hours': Decimal('10'),
    }
    with pytest.raises(RefreshValidationError, match='contain cas'):
        _service()._normalize_row(row)


def test_aggregate_rows_by_week_and_employee_sums_daily_rows() -> None:
    service = _service()
    rows = [
        service._normalize_row({'date': date(2026, 4, 28), 'cas': 'cas001', 'hours': Decimal('3')}),
        service._normalize_row({'date': date(2026, 4, 29), 'cas': 'cas001', 'hours': Decimal('5')}),
    ]

    aggregated = service._aggregate_rows_by_week_and_employee(rows)
    assert len(aggregated) == 1
    assert aggregated[0].week_start_date == date(2026, 4, 27)
    assert aggregated[0].hours == Decimal('8')
    assert aggregated[0].pshe == Decimal('0.2')
    assert aggregated[0].load_percent == Decimal('20')
