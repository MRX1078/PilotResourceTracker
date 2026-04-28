from __future__ import annotations

from datetime import date, datetime, timedelta


def to_week_start(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        base = value.date()
    elif isinstance(value, date):
        base = value
    elif isinstance(value, str):
        base = datetime.fromisoformat(value).date()
    else:
        raise ValueError(f'Unsupported date type: {type(value)!r}')

    return base - timedelta(days=base.weekday())
