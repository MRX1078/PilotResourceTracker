from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.assignment import PilotEmployeeAssignment
from app.models.employee import Employee
from app.models.enums import AccountingMode, AssignmentSource, QueryRunStatus
from app.models.pilot import Pilot
from app.models.trino_query_run import TrinoQueryRun
from app.schemas.refresh import RefreshAllError, RefreshAllResponse, RefreshPilotResponse
from app.services.metrics_service import as_decimal, normalize_assignment_values, recompute_pilot_metrics
from app.services.trino_service import TrinoConnectionOptions, TrinoQueryResult, TrinoService
from app.utils.week import to_week_start


class RefreshValidationError(ValueError):
    pass


@dataclass
class _NormalizedTrinoRow:
    week_start_date: date
    cas: str | None
    full_name: str | None
    rc: str | None
    hours: Decimal
    load_percent: Decimal
    pshe: Decimal


class RefreshService:
    REQUIRED_COLUMNS_BASE = {'hours'}
    WEEK_COLUMN_CANDIDATES = ('week_start_date',)
    DATE_COLUMN_CANDIDATES = ('date', 'work_date', 'event_date')

    def __init__(self, session: Session, trino_service: TrinoService | None = None) -> None:
        self.session = session
        self.trino_service = trino_service or TrinoService()

    def _get_or_create_employee(self, cas: str | None, full_name: str | None, rc: str | None) -> Employee:
        employee: Employee | None = None

        if cas:
            employee = self.session.scalar(select(Employee).where(Employee.cas == cas))

        if employee:
            if full_name and employee.full_name != full_name:
                employee.full_name = full_name
            if rc and employee.rc != rc:
                employee.rc = rc
            return employee

        # CAS-first matching flow: when only cas is provided and employee is not found,
        # we ask user to preload employees, or provide full_name+rc in SQL for auto-create.
        if cas and not employee and not (full_name and rc):
            raise RefreshValidationError(
                f'Employee with CAS `{cas}` was not found in directory. '
                'Import employees first or include full_name and rc in SQL result.'
            )

        if not employee:
            if full_name and rc:
                employee = self.session.scalar(
                    select(Employee).where(Employee.full_name == full_name, Employee.rc == rc)
                )

        if employee:
            if cas and not employee.cas:
                employee.cas = cas
            return employee

        if not (full_name and rc):
            raise RefreshValidationError(
                'Employee identity is incomplete: provide cas, or full_name + rc in SQL result.'
            )

        employee = Employee(cas=cas, full_name=full_name, rc=rc)
        self.session.add(employee)
        self.session.flush()
        return employee

    def _validate_columns(self, result: TrinoQueryResult) -> None:
        columns_lower = {column.lower() for column in result.columns}
        missing_columns = self.REQUIRED_COLUMNS_BASE.difference(columns_lower)
        if missing_columns:
            missing = ', '.join(sorted(missing_columns))
            raise RefreshValidationError(
                f'SQL query result is missing required columns: {missing}. '
                f'Expected at least: {", ".join(sorted(self.REQUIRED_COLUMNS_BASE))}'
            )

        has_week_or_date = any(column in columns_lower for column in self.WEEK_COLUMN_CANDIDATES) or any(
            column in columns_lower for column in self.DATE_COLUMN_CANDIDATES
        )
        if not has_week_or_date:
            raise RefreshValidationError(
                'SQL query result must include `week_start_date`, or one of date columns: '
                '`date`, `work_date`, `event_date`.'
            )

        has_cas = 'cas' in columns_lower
        has_full_name_rc = {'full_name', 'rc'}.issubset(columns_lower)
        if not has_cas and not has_full_name_rc:
            raise RefreshValidationError(
                'SQL query result must include employee identifier columns: '
                '`cas`, or both `full_name` and `rc`.'
            )

    @staticmethod
    def _get_row_value(row: dict[str, Any], *candidates: str) -> Any:
        lowered_candidates = {candidate.lower() for candidate in candidates}
        for key, value in row.items():
            if key.lower() in lowered_candidates:
                return value
        return None

    def _extract_week_start_date(self, row: dict[str, Any]) -> date:
        week_value = self._get_row_value(row, *self.WEEK_COLUMN_CANDIDATES)
        if week_value is None:
            week_value = self._get_row_value(row, *self.DATE_COLUMN_CANDIDATES)
        if week_value is None:
            raise RefreshValidationError(
                'Each SQL row should include `week_start_date` or one of date columns: '
                '`date`, `work_date`, `event_date`.'
            )
        return to_week_start(week_value)

    def _normalize_row(self, row: dict[str, Any]) -> _NormalizedTrinoRow:
        week_start_date = self._extract_week_start_date(row)
        cas_raw = self._get_row_value(row, 'cas')
        cas = str(cas_raw).strip() if cas_raw is not None and str(cas_raw).strip() else None
        full_name_raw = self._get_row_value(row, 'full_name')
        rc_raw = self._get_row_value(row, 'rc')
        full_name = str(full_name_raw).strip() if full_name_raw is not None and str(full_name_raw).strip() else None
        rc = str(rc_raw).strip() if rc_raw is not None and str(rc_raw).strip() else None

        if not cas and not (full_name and rc):
            raise RefreshValidationError(
                'Each SQL row should contain cas, or both full_name and rc.'
            )

        hours = as_decimal(self._get_row_value(row, 'hours'))
        if hours < 0:
            raise RefreshValidationError('hours should not be negative')

        load_percent_raw = self._get_row_value(row, 'load_percent')

        norm_hours, norm_pshe, norm_load = normalize_assignment_values(
            hours=hours,
            pshe=None,
            load_percent=as_decimal(load_percent_raw) if load_percent_raw is not None else None,
            work_hours_per_week=Decimal(str(settings.work_hours_per_week)),
        )

        return _NormalizedTrinoRow(
            week_start_date=week_start_date,
            cas=cas,
            full_name=full_name,
            rc=rc,
            hours=norm_hours,
            load_percent=norm_load,
            pshe=norm_pshe,
        )

    def _aggregate_rows_by_week_and_employee(
        self, rows: list[_NormalizedTrinoRow]
    ) -> list[_NormalizedTrinoRow]:
        if not rows:
            return []

        buckets: dict[tuple[date, str], _NormalizedTrinoRow] = {}

        for item in rows:
            identity = f'cas:{item.cas.lower()}' if item.cas else f'name_rc:{item.full_name.lower()}|{item.rc.lower()}'
            key = (item.week_start_date, identity)
            existing = buckets.get(key)
            if not existing:
                buckets[key] = _NormalizedTrinoRow(
                    week_start_date=item.week_start_date,
                    cas=item.cas,
                    full_name=item.full_name,
                    rc=item.rc,
                    hours=item.hours,
                    load_percent=Decimal('0'),
                    pshe=Decimal('0'),
                )
                continue

            existing.hours += item.hours
            if not existing.full_name and item.full_name:
                existing.full_name = item.full_name
            if not existing.rc and item.rc:
                existing.rc = item.rc

        work_hours_per_week = Decimal(str(settings.work_hours_per_week))
        aggregated_rows: list[_NormalizedTrinoRow] = []
        for row in buckets.values():
            norm_hours, norm_pshe, norm_load = normalize_assignment_values(
                hours=row.hours,
                pshe=None,
                load_percent=None,
                work_hours_per_week=work_hours_per_week,
            )
            row.hours = norm_hours
            row.pshe = norm_pshe
            row.load_percent = norm_load
            aggregated_rows.append(row)

        aggregated_rows.sort(key=lambda item: (item.week_start_date, item.cas or '', item.full_name or '', item.rc or ''))
        return aggregated_rows

    def _create_query_run(self, pilot_id: int) -> TrinoQueryRun:
        run = TrinoQueryRun(
            pilot_id=pilot_id,
            status=QueryRunStatus.RUNNING,
            started_at=datetime.utcnow(),
            rows_returned=0,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def _mark_run_failed(self, run_id: int, error_message: str) -> None:
        run = self.session.get(TrinoQueryRun, run_id)
        if not run:
            return
        run.status = QueryRunStatus.FAILED
        run.finished_at = datetime.utcnow()
        run.error_message = error_message[:4000]
        self.session.commit()

    def _mark_run_success(self, run_id: int, rows_returned: int) -> None:
        run = self.session.get(TrinoQueryRun, run_id)
        if not run:
            return
        run.status = QueryRunStatus.SUCCESS
        run.finished_at = datetime.utcnow()
        run.rows_returned = rows_returned
        run.error_message = None
        self.session.commit()

    @staticmethod
    def _pilot_connection_options(pilot: Pilot) -> TrinoConnectionOptions | None:
        has_overrides = any(
            (
                pilot.trino_host,
                pilot.trino_port is not None,
                pilot.trino_user,
                pilot.trino_password,
                pilot.trino_catalog,
                pilot.trino_schema,
                pilot.trino_http_scheme,
            )
        )
        if not has_overrides:
            return None

        return TrinoConnectionOptions(
            host=pilot.trino_host,
            port=pilot.trino_port,
            user=pilot.trino_user,
            password=pilot.trino_password,
            catalog=pilot.trino_catalog,
            schema=pilot.trino_schema,
            http_scheme=pilot.trino_http_scheme,
        )

    def refresh_single_pilot(self, pilot_id: int) -> RefreshPilotResponse:
        pilot = self.session.get(Pilot, pilot_id)
        if not pilot or not pilot.is_active:
            raise ValueError('Pilot not found or inactive')

        if pilot.accounting_mode != AccountingMode.SQL:
            raise ValueError('Refresh is available only for SQL-mode pilots')

        if not pilot.sql_query:
            raise ValueError('Pilot SQL query is empty')

        run = self._create_query_run(pilot.id)

        try:
            result = self.trino_service.execute_query(
                pilot.sql_query,
                connection_options=self._pilot_connection_options(pilot),
            )
            self._validate_columns(result)
            normalized_rows = [self._normalize_row(row) for row in result.rows]
            aggregated_rows = self._aggregate_rows_by_week_and_employee(normalized_rows)

            self.session.execute(
                delete(PilotEmployeeAssignment).where(
                    PilotEmployeeAssignment.pilot_id == pilot.id,
                    PilotEmployeeAssignment.source == AssignmentSource.SQL,
                )
            )

            for item in aggregated_rows:
                employee = self._get_or_create_employee(item.cas, item.full_name, item.rc)
                assignment = PilotEmployeeAssignment(
                    pilot_id=pilot.id,
                    employee_id=employee.id,
                    week_start_date=item.week_start_date,
                    load_percent=item.load_percent,
                    pshe=item.pshe,
                    hours=item.hours,
                    source=AssignmentSource.SQL,
                )
                self.session.add(assignment)

            self.session.flush()
            recompute_pilot_metrics(self.session, pilot.id)
            self.session.commit()
            self._mark_run_success(run.id, len(normalized_rows))

            aggregated_count = len(aggregated_rows)
            source_rows_count = len(normalized_rows)
            message = 'Pilot refreshed successfully'
            if aggregated_count != source_rows_count:
                message = (
                    'Pilot refreshed successfully. '
                    f'Aggregated {source_rows_count} source rows into {aggregated_count} weekly assignments.'
                )

            return RefreshPilotResponse(
                pilot_id=pilot.id,
                pilot_name=pilot.name,
                rows_processed=aggregated_count,
                message=message,
            )

        except Exception as exc:
            self.session.rollback()
            self._mark_run_failed(run.id, str(exc))
            raise

    def refresh_all_sql_pilots(self) -> RefreshAllResponse:
        pilots = self.session.scalars(
            select(Pilot).where(
                Pilot.is_active.is_(True),
                Pilot.accounting_mode == AccountingMode.SQL,
            )
        ).all()

        success_count = 0
        errors: list[RefreshAllError] = []

        for pilot in pilots:
            try:
                self.refresh_single_pilot(pilot.id)
                success_count += 1
            except Exception as exc:
                errors.append(
                    RefreshAllError(
                        pilot_id=pilot.id,
                        pilot_name=pilot.name,
                        error=str(exc),
                    )
                )

        return RefreshAllResponse(
            success_count=success_count,
            failed_count=len(errors),
            errors=errors,
        )

    def validate_sql_query(
        self,
        sql_query: str,
        connection_options: TrinoConnectionOptions | None = None,
    ) -> tuple[bool, list[str], str]:
        try:
            result = self.trino_service.validate_query(sql_query, connection_options=connection_options)
            self._validate_columns(result)
            return True, result.columns, 'SQL query looks valid.'
        except Exception as exc:
            return False, [], f'SQL validation failed: {exc}'
