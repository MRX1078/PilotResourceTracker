from __future__ import annotations

import enum
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.assignment import PilotEmployeeAssignment
from app.models.employee import Employee
from app.models.pilot import Pilot
from app.models.pilot_weekly_metric import PilotWeeklyMetric
from app.models.trino_query_run import TrinoQueryRun
from app.schemas.backup import BackupCounts, BackupImportResponse, BackupSettings
from app.services.refresh_service import RefreshService


class BackupValidationError(ValueError):
    pass


class BackupService:
    BACKUP_VERSION = '1.0'

    TABLE_MODELS = {
        'pilots': Pilot,
        'employees': Employee,
        'pilot_employee_assignments': PilotEmployeeAssignment,
        'pilot_weekly_metrics': PilotWeeklyMetric,
        'trino_query_runs': TrinoQueryRun,
    }

    DELETE_ORDER = [
        TrinoQueryRun,
        PilotWeeklyMetric,
        PilotEmployeeAssignment,
        Employee,
        Pilot,
    ]

    INSERT_ORDER = [
        Pilot,
        Employee,
        PilotEmployeeAssignment,
        PilotWeeklyMetric,
        TrinoQueryRun,
    ]

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, enum.Enum):
            return value.value
        return value

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if value in (None, ''):
            return None
        normalized = value.replace('Z', '+00:00')
        return datetime.fromisoformat(normalized)

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if value in (None, ''):
            return None
        return date.fromisoformat(value)

    @staticmethod
    def _deserialize_value(model: Any, column_name: str, raw_value: Any) -> Any:
        if raw_value is None:
            return None

        column = model.__table__.columns[column_name]
        python_type = getattr(column.type, 'python_type', None)

        if python_type is Decimal:
            return Decimal(str(raw_value))
        if python_type is datetime:
            return BackupService._parse_datetime(str(raw_value))
        if python_type is date:
            return BackupService._parse_date(str(raw_value))

        enum_class = getattr(column.type, 'enum_class', None)
        if enum_class is not None:
            return enum_class(raw_value)

        return raw_value

    def _serialize_model_rows(self, model: Any) -> list[dict[str, Any]]:
        rows = self.session.query(model).order_by(model.id).all()
        serialized_rows: list[dict[str, Any]] = []

        for row in rows:
            item: dict[str, Any] = {}
            for column in model.__table__.columns:
                value = getattr(row, column.name)
                item[column.name] = self._serialize_value(value)
            serialized_rows.append(item)

        return serialized_rows

    def _deserialize_model_rows(self, model: Any, rows: list[dict[str, Any]]) -> list[Any]:
        objects: list[Any] = []
        allowed_columns = {column.name for column in model.__table__.columns}

        for row in rows:
            payload: dict[str, Any] = {}
            for key, value in row.items():
                if key not in allowed_columns:
                    continue
                payload[key] = self._deserialize_value(model, key, value)
            objects.append(model(**payload))

        return objects

    @staticmethod
    def _build_counts(snapshot_data: dict[str, list[dict[str, Any]]]) -> BackupCounts:
        return BackupCounts(
            pilots=len(snapshot_data.get('pilots', [])),
            employees=len(snapshot_data.get('employees', [])),
            assignments=len(snapshot_data.get('pilot_employee_assignments', [])),
            metrics=len(snapshot_data.get('pilot_weekly_metrics', [])),
            trino_query_runs=len(snapshot_data.get('trino_query_runs', [])),
        )

    def export_snapshot(self) -> dict[str, Any]:
        data: dict[str, list[dict[str, Any]]] = {}

        for key, model in self.TABLE_MODELS.items():
            data[key] = self._serialize_model_rows(model)

        settings_payload = BackupSettings(
            work_hours_per_week=settings.work_hours_per_week,
            cost_per_minute=settings.cost_per_minute,
        )

        return {
            'version': self.BACKUP_VERSION,
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'settings': settings_payload.model_dump(),
            'counts': self._build_counts(data).model_dump(),
            'data': data,
        }

    def export_snapshot_json_bytes(self) -> bytes:
        snapshot = self.export_snapshot()
        return json.dumps(snapshot, ensure_ascii=False, indent=2).encode('utf-8')

    @staticmethod
    def _validate_snapshot(snapshot: dict[str, Any]) -> None:
        if not isinstance(snapshot, dict):
            raise BackupValidationError('Backup file should contain a JSON object')

        if 'data' not in snapshot or not isinstance(snapshot['data'], dict):
            raise BackupValidationError('Backup file is invalid: missing `data` section')

        required_sections = {
            'pilots',
            'employees',
            'pilot_employee_assignments',
            'pilot_weekly_metrics',
            'trino_query_runs',
        }

        missing_sections = required_sections.difference(set(snapshot['data'].keys()))
        if missing_sections:
            raise BackupValidationError(
                f'Backup file is invalid: missing sections {", ".join(sorted(missing_sections))}'
            )

    def _reset_identity_sequences(self) -> None:
        table_names = [
            'pilots',
            'employees',
            'pilot_employee_assignments',
            'pilot_weekly_metrics',
            'trino_query_runs',
        ]

        for table_name in table_names:
            self.session.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), "
                    f"(SELECT COUNT(*) > 0 FROM {table_name}))"
                )
            )

    def import_snapshot(
        self,
        snapshot: dict[str, Any],
        run_refresh_all_sql: bool = False,
    ) -> BackupImportResponse:
        self._validate_snapshot(snapshot)

        snapshot_data = snapshot['data']
        warnings: list[str] = []

        settings_from_backup = BackupSettings(
            work_hours_per_week=float(snapshot.get('settings', {}).get('work_hours_per_week', settings.work_hours_per_week)),
            cost_per_minute=float(snapshot.get('settings', {}).get('cost_per_minute', settings.cost_per_minute)),
        )

        if settings_from_backup.work_hours_per_week != settings.work_hours_per_week:
            warnings.append(
                'WORK_HOURS_PER_WEEK in backup differs from current environment. '
                f'Backup: {settings_from_backup.work_hours_per_week}, current: {settings.work_hours_per_week}.'
            )

        if settings_from_backup.cost_per_minute != settings.cost_per_minute:
            warnings.append(
                'COST_PER_MINUTE in backup differs from current environment. '
                f'Backup: {settings_from_backup.cost_per_minute}, current: {settings.cost_per_minute}.'
            )

        try:
            for model in self.DELETE_ORDER:
                self.session.execute(delete(model))

            for model in self.INSERT_ORDER:
                key = next(table_key for table_key, table_model in self.TABLE_MODELS.items() if table_model is model)
                objects = self._deserialize_model_rows(model, snapshot_data.get(key, []))
                self.session.add_all(objects)

            self.session.flush()
            self._reset_identity_sequences()
            self.session.commit()

        except Exception as exc:
            self.session.rollback()
            raise BackupValidationError(f'Import failed: {exc}') from exc

        refresh_result = None
        if run_refresh_all_sql:
            try:
                refresh_result = RefreshService(self.session).refresh_all_sql_pilots()
                if refresh_result.failed_count > 0:
                    warnings.append(
                        f'Refresh-all completed with {refresh_result.failed_count} errors after import.'
                    )
            except Exception as exc:
                warnings.append(f'Failed to run refresh-all after import: {exc}')

        return BackupImportResponse(
            message='Backup imported successfully',
            imported_at=datetime.utcnow(),
            imported=self._build_counts(snapshot_data),
            settings_from_backup=settings_from_backup,
            refresh_all_result=refresh_result,
            warnings=warnings,
        )
