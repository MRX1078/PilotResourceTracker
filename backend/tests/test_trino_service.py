import pytest

from app.services.trino_service import TrinoConfigurationError, TrinoConnectionOptions, TrinoService


def test_trino_requires_host_and_user_only() -> None:
    options = TrinoConnectionOptions(
        host='trino.example.local',
        user='svc_user',
        catalog=None,
        schema=None,
    )
    TrinoService._ensure_configured(options)


def test_trino_rejects_missing_host_or_user() -> None:
    with pytest.raises(TrinoConfigurationError, match='TRINO_HOST and TRINO_USER'):
        TrinoService._ensure_configured(TrinoConnectionOptions(host=None, user='svc_user'))

    with pytest.raises(TrinoConfigurationError, match='TRINO_HOST and TRINO_USER'):
        TrinoService._ensure_configured(TrinoConnectionOptions(host='trino.example.local', user=None))


def test_trino_rejects_schema_without_catalog() -> None:
    with pytest.raises(TrinoConfigurationError, match='TRINO_SCHEMA requires TRINO_CATALOG'):
        TrinoService._ensure_configured(
            TrinoConnectionOptions(
                host='trino.example.local',
                user='svc_user',
                catalog=None,
                schema='analytics',
            )
        )
