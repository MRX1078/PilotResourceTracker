from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import trino
from trino.auth import BasicAuthentication

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
    def __init__(self) -> None:
        self.host = settings.trino_host
        self.port = settings.trino_port
        self.user = settings.trino_user
        self.password = settings.trino_password
        self.catalog = settings.trino_catalog
        self.schema = settings.trino_schema
        self.http_scheme = settings.trino_http_scheme

    def _resolve_connection(self, overrides: TrinoConnectionOptions | None = None) -> TrinoConnectionOptions:
        if overrides is None:
            return TrinoConnectionOptions(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                catalog=self.catalog,
                schema=self.schema,
                http_scheme=self.http_scheme,
            )

        return TrinoConnectionOptions(
            host=overrides.host or self.host,
            port=overrides.port if overrides.port is not None else self.port,
            user=overrides.user or self.user,
            password=overrides.password if overrides.password is not None else self.password,
            catalog=overrides.catalog or self.catalog,
            schema=overrides.schema or self.schema,
            http_scheme=overrides.http_scheme or self.http_scheme,
        )

    @staticmethod
    def _ensure_configured(connection: TrinoConnectionOptions) -> None:
        if not connection.host or not connection.user or not connection.catalog or not connection.schema:
            raise TrinoConfigurationError(
                'Trino is not configured. Please set TRINO_HOST, TRINO_USER, TRINO_CATALOG and TRINO_SCHEMA '
                'in environment, or fill Trino connection fields in SQL pilot settings.'
            )

    def _connect(self, overrides: TrinoConnectionOptions | None = None) -> trino.dbapi.Connection:
        connection = self._resolve_connection(overrides)
        self._ensure_configured(connection)

        assert connection.host is not None
        assert connection.user is not None
        assert connection.catalog is not None
        assert connection.schema is not None

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
