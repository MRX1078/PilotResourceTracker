from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import trino
from trino.auth import BasicAuthentication
from sqlalchemy.orm import Session

from app.config import settings


class TrinoConfigurationError(RuntimeError):
    pass


@dataclass
class TrinoQueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]


@dataclass
class TrinoConnectionOptions:
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    catalog: str | None = None
    schema: str | None = None
    http_scheme: str | None = None


class TrinoService:
    """Trino client. Reads connection settings from (in priority order):

    1. explicit `connection_options` passed to a method call,
    2. the DB-backed `app_settings` singleton (if a session is provided),
    3. environment variables loaded into `app.config.settings`.
    """

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self.host = settings.trino_host
        self.port = settings.trino_port
        self.user = settings.trino_user
        self.password = settings.trino_password
        self.catalog = settings.trino_catalog
        self.schema = settings.trino_schema
        self.http_scheme = settings.trino_http_scheme

    def _db_settings(self) -> TrinoConnectionOptions | None:
        if self.session is None:
            return None

        # Local import to avoid circular import at module load time.
        from app.services.app_settings_service import AppSettingsService

        instance = AppSettingsService(self.session).get()
        return TrinoConnectionOptions(
            host=instance.trino_host,
            port=instance.trino_port,
            user=instance.trino_user,
            password=instance.trino_password,
            catalog=instance.trino_catalog,
            schema=instance.trino_schema,
            http_scheme=instance.trino_http_scheme,
        )

    def _resolve_connection(self, overrides: TrinoConnectionOptions | None = None) -> TrinoConnectionOptions:
        layers: list[TrinoConnectionOptions] = []
        if overrides is not None:
            layers.append(overrides)

        db_layer = self._db_settings()
        if db_layer is not None:
            layers.append(db_layer)

        env_layer = TrinoConnectionOptions(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            catalog=self.catalog,
            schema=self.schema,
            http_scheme=self.http_scheme,
        )
        layers.append(env_layer)

        def pick(field: str) -> Any:
            for layer in layers:
                value = getattr(layer, field)
                if value not in (None, ''):
                    return value
            return None

        return TrinoConnectionOptions(
            host=pick('host'),
            port=pick('port'),
            user=pick('user'),
            password=pick('password'),
            catalog=pick('catalog'),
            schema=pick('schema'),
            http_scheme=pick('http_scheme'),
        )

    @staticmethod
    def _ensure_configured(connection: TrinoConnectionOptions) -> None:
        if not connection.host or not connection.user:
            raise TrinoConfigurationError(
                'Trino is not configured. Please set TRINO_HOST and TRINO_USER '
                'on the Backups page (Подключение к Trino) or in environment.'
            )
        if connection.schema and not connection.catalog:
            raise TrinoConfigurationError(
                'Trino connection is invalid: TRINO_SCHEMA requires TRINO_CATALOG.'
            )

    def _connect(self, overrides: TrinoConnectionOptions | None = None) -> trino.dbapi.Connection:
        connection = self._resolve_connection(overrides)
        self._ensure_configured(connection)

        assert connection.host is not None
        assert connection.user is not None

        auth = BasicAuthentication(connection.user, connection.password) if connection.password else None
        return trino.dbapi.connect(
            host=connection.host,
            port=connection.port or settings.trino_port,
            user=connection.user,
            catalog=connection.catalog,
            schema=connection.schema,
            http_scheme=connection.http_scheme or settings.trino_http_scheme,
            auth=auth,
        )

    def execute_query(
        self,
        sql_query: str,
        connection_options: TrinoConnectionOptions | None = None,
    ) -> TrinoQueryResult:
        connection = self._connect(connection_options)
        cursor = connection.cursor()
        try:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description] if cursor.description else []
            normalized_rows = [dict(zip(columns, row, strict=False)) for row in rows]
            return TrinoQueryResult(columns=columns, rows=normalized_rows)
        finally:
            cursor.close()
            connection.close()

    def validate_query(
        self,
        sql_query: str,
        connection_options: TrinoConnectionOptions | None = None,
    ) -> TrinoQueryResult:
        normalized = sql_query.strip().rstrip(';')
        validation_query = f'SELECT * FROM ({normalized}) AS validation_query LIMIT 1'
        return self.execute_query(validation_query, connection_options=connection_options)
