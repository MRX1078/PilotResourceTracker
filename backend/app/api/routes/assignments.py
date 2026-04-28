from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.config import settings
from app.database import get_db
from app.models.assignment import PilotEmployeeAssignment
from app.models.employee import Employee
from app.models.enums import AccountingMode, AssignmentSource
from app.models.pilot import Pilot
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentCsvImportError,
    AssignmentCsvImportResponse,
    AssignmentEmployeeInfo,
    AssignmentRead,
    AssignmentUpdate,
    OtherPilotInfo,
)
from app.services.metrics_service import normalize_assignment_values, recompute_weekly_metric
from app.utils.week import to_week_start

router = APIRouter()


def _normalize_csv_row(row: dict[str, str | None]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized_key = key.strip().lower()
        normalized_value = str(value).strip() if value is not None else ''
        normalized[normalized_key] = normalized_value
    return normalized


def _parse_optional_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned == '':
        return None
    cleaned = cleaned.replace(',', '.')
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f'Invalid decimal value: {value}') from exc


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned == '':
        return None
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ValueError(f'Invalid integer value: {value}') from exc


def _parse_source(value: str | None) -> AssignmentSource:
    source_value = (value or AssignmentSource.MANUAL.value).strip().lower()
    try:
        return AssignmentSource(source_value)
    except ValueError as exc:
        raise ValueError(f'Invalid source value: {source_value}. Use manual or sql') from exc


def _decode_csv_content(raw_bytes: bytes) -> str:
    for encoding in ('utf-8-sig', 'utf-8', 'cp1251'):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('Unable to decode CSV. Supported encodings: utf-8, utf-8-sig, cp1251')


def _detect_delimiter(content: str) -> str:
    sample = '\n'.join(content.splitlines()[:5])
    if not sample:
        return ','
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=';,\t')
        return dialect.delimiter
    except csv.Error:
        semicolons = sample.count(';')
        commas = sample.count(',')
        tabs = sample.count('\t')
        if semicolons >= commas and semicolons >= tabs:
            return ';'
        if tabs > commas:
            return '\t'
        return ','


def _get_other_pilots(db: Session, employee_id: int, pilot_id: int) -> list[OtherPilotInfo]:
    other_pilots_rows = db.execute(
        select(Pilot.id, Pilot.name)
        .join(PilotEmployeeAssignment, PilotEmployeeAssignment.pilot_id == Pilot.id)
        .where(
            and_(
                PilotEmployeeAssignment.employee_id == employee_id,
                Pilot.id != pilot_id,
                Pilot.is_active.is_(True),
            )
        )
        .distinct()
        .order_by(Pilot.name)
    ).all()
    return [OtherPilotInfo(pilot_id=row[0], pilot_name=row[1]) for row in other_pilots_rows]


def _resolve_employee(db: Session, payload: AssignmentCreate) -> Employee:
    employee: Employee | None = None

    if payload.employee_id:
        employee = db.get(Employee, payload.employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail=f'Employee with id={payload.employee_id} not found')

    if employee:
        return employee

    full_name = payload.full_name.strip() if payload.full_name else None
    rc = payload.rc.strip() if payload.rc else None
    cas = payload.cas.strip() if payload.cas else None

    if cas:
        employee = db.scalar(select(Employee).where(Employee.cas == cas))
        if employee:
            return employee
        if not (full_name and rc):
            raise HTTPException(
                status_code=400,
                detail=(
                    f'Employee with CAS `{cas}` not found. '
                    'Import employees first, or provide full_name + rc to create a new employee.'
                ),
            )

    if (full_name and not rc) or (rc and not full_name):
        raise HTTPException(status_code=400, detail='Provide both full_name and rc when creating a new employee')

    if full_name and rc:
        employee = db.scalar(select(Employee).where(Employee.full_name == full_name, Employee.rc == rc))
        if employee:
            if cas and employee.cas and employee.cas != cas:
                raise HTTPException(
                    status_code=400,
                    detail=f'Employee {full_name} ({rc}) already linked to another CAS: {employee.cas}',
                )
            if cas and not employee.cas:
                employee.cas = cas
            return employee

        employee = Employee(cas=cas, full_name=full_name, rc=rc)
        db.add(employee)
        db.flush()
        return employee

    raise HTTPException(
        status_code=400,
        detail='Provide employee_id, or CAS of existing employee, or full_name + rc for a new employee',
    )


def _upsert_assignment(
    db: Session,
    pilot: Pilot,
    payload: AssignmentCreate,
) -> tuple[PilotEmployeeAssignment, bool, date]:
    if pilot.accounting_mode != AccountingMode.MANUAL and payload.source == AssignmentSource.MANUAL:
        raise HTTPException(status_code=400, detail='Manual assignments are allowed only for manual-mode pilots')

    employee = _resolve_employee(db, payload)

    work_hours = Decimal(str(settings.work_hours_per_week))
    hours, pshe, load_percent = normalize_assignment_values(
        hours=payload.hours,
        pshe=payload.pshe,
        load_percent=payload.load_percent,
        work_hours_per_week=work_hours,
    )

    normalized_week = to_week_start(payload.week_start_date)

    assignment = db.scalar(
        select(PilotEmployeeAssignment).where(
            PilotEmployeeAssignment.pilot_id == pilot.id,
            PilotEmployeeAssignment.employee_id == employee.id,
            PilotEmployeeAssignment.week_start_date == normalized_week,
            PilotEmployeeAssignment.source == payload.source,
        )
    )

    created = assignment is None
    if created:
        assignment = PilotEmployeeAssignment(
            pilot_id=pilot.id,
            employee_id=employee.id,
            week_start_date=normalized_week,
            source=payload.source,
        )
        db.add(assignment)

    assignment.hours = hours
    assignment.pshe = pshe
    assignment.load_percent = load_percent

    db.flush()
    return assignment, created, normalized_week


def _to_assignment_read(db: Session, assignment_id: int) -> AssignmentRead:
    assignment = db.scalar(
        select(PilotEmployeeAssignment)
        .options(joinedload(PilotEmployeeAssignment.employee))
        .where(PilotEmployeeAssignment.id == assignment_id)
    )
    if not assignment:
        raise HTTPException(status_code=404, detail='Assignment not found')

    return AssignmentRead(
        id=assignment.id,
        pilot_id=assignment.pilot_id,
        employee_id=assignment.employee_id,
        week_start_date=assignment.week_start_date,
        load_percent=assignment.load_percent,
        pshe=assignment.pshe,
        hours=assignment.hours,
        source=assignment.source,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        employee=AssignmentEmployeeInfo(
            id=assignment.employee.id,
            cas=assignment.employee.cas,
            full_name=assignment.employee.full_name,
            rc=assignment.employee.rc,
        ),
        other_pilots=_get_other_pilots(db, assignment.employee_id, assignment.pilot_id),
    )


@router.get('/pilots/{pilot_id}/assignments', response_model=list[AssignmentRead])
def list_pilot_assignments(
    pilot_id: int,
    week_start_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AssignmentRead]:
    pilot = db.get(Pilot, pilot_id)
    if not pilot or not pilot.is_active:
        raise HTTPException(status_code=404, detail='Pilot not found')

    stmt = (
        select(PilotEmployeeAssignment)
        .options(joinedload(PilotEmployeeAssignment.employee))
        .where(PilotEmployeeAssignment.pilot_id == pilot_id)
        .order_by(PilotEmployeeAssignment.week_start_date.desc(), PilotEmployeeAssignment.id.desc())
    )
    if week_start_date:
        stmt = stmt.where(PilotEmployeeAssignment.week_start_date == to_week_start(week_start_date))

    assignments = db.scalars(stmt).all()

    response: list[AssignmentRead] = []
    for assignment in assignments:
        response.append(
            AssignmentRead(
                id=assignment.id,
                pilot_id=assignment.pilot_id,
                employee_id=assignment.employee_id,
                week_start_date=assignment.week_start_date,
                load_percent=assignment.load_percent,
                pshe=assignment.pshe,
                hours=assignment.hours,
                source=assignment.source,
                created_at=assignment.created_at,
                updated_at=assignment.updated_at,
                employee=AssignmentEmployeeInfo(
                    id=assignment.employee.id,
                    cas=assignment.employee.cas,
                    full_name=assignment.employee.full_name,
                    rc=assignment.employee.rc,
                ),
                other_pilots=_get_other_pilots(db, assignment.employee_id, pilot_id),
            )
        )

    return response


@router.post('/pilots/{pilot_id}/assignments', response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    pilot_id: int,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
) -> AssignmentRead:
    pilot = db.get(Pilot, pilot_id)
    if not pilot or not pilot.is_active:
        raise HTTPException(status_code=404, detail='Pilot not found')

    assignment, _, normalized_week = _upsert_assignment(db, pilot, payload)
    recompute_weekly_metric(db, pilot_id, normalized_week)
    db.commit()

    return _to_assignment_read(db, assignment.id)


@router.post('/pilots/{pilot_id}/assignments/import-csv', response_model=AssignmentCsvImportResponse)
async def import_assignments_csv(
    pilot_id: int,
    file: UploadFile = File(...),
    delimiter: str | None = Query(default=None, min_length=1, max_length=1),
    db: Session = Depends(get_db),
) -> AssignmentCsvImportResponse:
    pilot = db.get(Pilot, pilot_id)
    if not pilot or not pilot.is_active:
        raise HTTPException(status_code=404, detail='Pilot not found')

    if pilot.accounting_mode != AccountingMode.MANUAL:
        raise HTTPException(status_code=400, detail='CSV import is available only for manual-mode pilots')

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail='CSV file is empty')

    try:
        content = _decode_csv_content(content_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resolved_delimiter = delimiter or _detect_delimiter(content)
    reader = csv.DictReader(io.StringIO(content), delimiter=resolved_delimiter)

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail='CSV should contain a header row')

    parsed_rows: list[tuple[int, AssignmentCreate]] = []
    parse_errors: list[AssignmentCsvImportError] = []

    for row_number, row in enumerate(reader, start=2):
        normalized_row = _normalize_csv_row(row)
        if not any(value for value in normalized_row.values()):
            continue

        try:
            payload = AssignmentCreate(
                employee_id=_parse_optional_int(normalized_row.get('employee_id')),
                cas=normalized_row.get('cas') or normalized_row.get('cas_id') or None,
                full_name=normalized_row.get('full_name') or normalized_row.get('fio') or normalized_row.get('name') or None,
                rc=normalized_row.get('rc') or None,
                week_start_date=normalized_row.get('week_start_date'),
                load_percent=_parse_optional_decimal(normalized_row.get('load_percent')),
                pshe=_parse_optional_decimal(normalized_row.get('pshe')),
                hours=_parse_optional_decimal(normalized_row.get('hours')),
                source=_parse_source(normalized_row.get('source')),
            )
            parsed_rows.append((row_number, payload))
        except (ValidationError, ValueError) as exc:
            parse_errors.append(AssignmentCsvImportError(row_number=row_number, error=str(exc)))

    if parse_errors:
        raise HTTPException(
            status_code=400,
            detail={
                'message': 'CSV validation failed',
                'errors': [error.model_dump() for error in parse_errors],
            },
        )

    if not parsed_rows:
        raise HTTPException(status_code=400, detail='No valid rows found in CSV')

    created_count = 0
    updated_count = 0
    weeks_affected: set[date] = set()
    apply_errors: list[AssignmentCsvImportError] = []

    for row_number, payload in parsed_rows:
        try:
            assignment, created, week_start = _upsert_assignment(db, pilot, payload)
            weeks_affected.add(week_start)
            if created:
                created_count += 1
            else:
                updated_count += 1
        except HTTPException as exc:
            apply_errors.append(AssignmentCsvImportError(row_number=row_number, error=str(exc.detail)))
        except Exception as exc:
            apply_errors.append(AssignmentCsvImportError(row_number=row_number, error=str(exc)))

    if apply_errors:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail={
                'message': 'CSV import failed. No rows were saved',
                'errors': [error.model_dump() for error in apply_errors],
            },
        )

    for week_start in sorted(weeks_affected):
        recompute_weekly_metric(db, pilot.id, week_start)

    db.commit()

    return AssignmentCsvImportResponse(
        total_rows=len(parsed_rows),
        imported_count=created_count + updated_count,
        created_count=created_count,
        updated_count=updated_count,
        weeks_affected=sorted(weeks_affected),
        errors=[],
    )


@router.put('/assignments/{assignment_id}', response_model=AssignmentRead)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
) -> AssignmentRead:
    assignment = db.scalar(
        select(PilotEmployeeAssignment)
        .options(joinedload(PilotEmployeeAssignment.employee))
        .where(PilotEmployeeAssignment.id == assignment_id)
    )

    if not assignment:
        raise HTTPException(status_code=404, detail='Assignment not found')

    old_week = assignment.week_start_date

    if payload.week_start_date is not None:
        assignment.week_start_date = to_week_start(payload.week_start_date)

    work_hours = Decimal(str(settings.work_hours_per_week))
    current_hours = payload.hours if payload.hours is not None else assignment.hours
    current_pshe = payload.pshe if payload.pshe is not None else assignment.pshe
    current_load = payload.load_percent if payload.load_percent is not None else assignment.load_percent

    hours, pshe, load_percent = normalize_assignment_values(
        hours=current_hours,
        pshe=current_pshe,
        load_percent=current_load,
        work_hours_per_week=work_hours,
    )

    assignment.hours = hours
    assignment.pshe = pshe
    assignment.load_percent = load_percent

    db.flush()

    recompute_weekly_metric(db, assignment.pilot_id, old_week)
    recompute_weekly_metric(db, assignment.pilot_id, assignment.week_start_date)

    db.commit()
    return _to_assignment_read(db, assignment.id)


@router.delete('/assignments/{assignment_id}')
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    assignment = db.get(PilotEmployeeAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail='Assignment not found')

    pilot_id = assignment.pilot_id
    week_start_date = assignment.week_start_date

    db.delete(assignment)
    db.flush()

    recompute_weekly_metric(db, pilot_id, week_start_date)
    db.commit()
    return {'message': 'Assignment deleted'}
