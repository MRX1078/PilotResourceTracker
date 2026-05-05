from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.database import get_db
from app.models.assignment import PilotEmployeeAssignment
from app.models.employee import Employee
from app.models.pilot import Pilot
from app.schemas.employee import (
    EmployeeCsvImportError,
    EmployeeCsvImportResponse,
    EmployeeDetail,
    EmployeePilotLoad,
    EmployeeRead,
    EmployeeWeeklyLoad,
)
from app.utils.week import to_week_start

router = APIRouter(prefix='/employees')


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


def _normalize_csv_row(row: dict[str, str | None]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized_key = key.strip().lower()
        normalized_value = str(value).strip() if value is not None else ''
        normalized[normalized_key] = normalized_value
    return normalized


@router.get('', response_model=list[EmployeeRead])
def list_employees(
    search: str | None = Query(default=None, description='Search by cas or full name'),
    db: Session = Depends(get_db),
) -> list[EmployeeRead]:
    stmt = select(Employee).order_by(Employee.full_name)
    if search:
        like_value = f'%{search.strip()}%'
        stmt = stmt.where((Employee.full_name.ilike(like_value)) | (Employee.cas.ilike(like_value)))

    return list(db.scalars(stmt).all())


@router.post('/import-csv', response_model=EmployeeCsvImportResponse)
async def import_employees_csv(
    file: UploadFile = File(...),
    delimiter: str | None = Query(default=None, min_length=1, max_length=1),
    db: Session = Depends(get_db),
) -> EmployeeCsvImportResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail='CSV file is empty')

    try:
        content = _decode_csv_content(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resolved_delimiter = delimiter or _detect_delimiter(content)
    reader = csv.DictReader(io.StringIO(content), delimiter=resolved_delimiter)

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail='CSV should contain a header row')

    errors: list[EmployeeCsvImportError] = []
    created_count = 0
    updated_count = 0
    total_rows = 0
    employees_cache: dict[str, Employee] = {}
    created_in_batch: set[str] = set()

    for row_number, row in enumerate(reader, start=2):
        normalized = _normalize_csv_row(row)
        if not any(normalized.values()):
            continue

        total_rows += 1

        cas = (normalized.get('cas_id') or normalized.get('cas') or '').strip()
        full_name = (normalized.get('full_name') or normalized.get('fio') or normalized.get('name') or '').strip()
        rc = (normalized.get('rc') or '').strip()

        if not cas:
            errors.append(EmployeeCsvImportError(row_number=row_number, error='Missing cas_id/cas'))
            continue

        if not full_name:
            errors.append(EmployeeCsvImportError(row_number=row_number, error='Missing full_name (or fio/name)'))
            continue

        if not rc:
            errors.append(EmployeeCsvImportError(row_number=row_number, error='Missing rc'))
            continue

        employee = employees_cache.get(cas)
        if employee is None:
            employee = db.scalar(select(Employee).where(Employee.cas == cas))
            if employee is not None:
                employees_cache[cas] = employee

        if not employee:
            employee = Employee(cas=cas, full_name=full_name, rc=rc)
            db.add(employee)
            employees_cache[cas] = employee
            created_in_batch.add(cas)
            created_count += 1
        else:
            changed = False
            if employee.full_name != full_name:
                employee.full_name = full_name
                changed = True
            if employee.rc != rc:
                employee.rc = rc
                changed = True
            if changed and cas not in created_in_batch:
                updated_count += 1

    if total_rows == 0:
        raise HTTPException(status_code=400, detail='CSV has no data rows')

    imported_count = created_count + updated_count

    if imported_count == 0 and errors:
        raise HTTPException(
            status_code=400,
            detail={
                'message': 'CSV import failed. No valid employee rows found.',
                'errors': [item.model_dump() for item in errors],
            },
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail='CSV import failed due to CAS uniqueness conflict. '
            'Please check duplicate or conflicting cas_id values.',
        ) from exc

    return EmployeeCsvImportResponse(
        total_rows=total_rows,
        imported_count=imported_count,
        created_count=created_count,
        updated_count=updated_count,
        errors=errors,
    )


@router.get('/by-cas/{cas}', response_model=EmployeeRead)
def get_employee_by_cas(cas: str, db: Session = Depends(get_db)) -> EmployeeRead:
    employee = db.scalar(select(Employee).where(Employee.cas == cas))
    if not employee:
        raise HTTPException(status_code=404, detail='Employee not found')
    return employee


@router.get('/{employee_id}', response_model=EmployeeDetail)
def get_employee(
    employee_id: int,
    week_start_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> EmployeeDetail:
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail='Employee not found')

    selected_week = to_week_start(week_start_date or date.today())

    pilot_rows = db.execute(
        select(
            Pilot.id,
            Pilot.name,
            PilotEmployeeAssignment.week_start_date,
            PilotEmployeeAssignment.load_percent,
            PilotEmployeeAssignment.hours,
            PilotEmployeeAssignment.pshe,
        )
        .join(Pilot, Pilot.id == PilotEmployeeAssignment.pilot_id)
        .where(PilotEmployeeAssignment.employee_id == employee_id)
        .order_by(PilotEmployeeAssignment.week_start_date.desc(), Pilot.name)
    ).all()

    selected_week_pilots = [
        EmployeePilotLoad(
            pilot_id=row[0],
            pilot_name=row[1],
            week_start_date=row[2],
            load_percent=row[3],
            hours=row[4],
            pshe=row[5],
        )
        for row in pilot_rows
        if row[2] == selected_week
    ]

    weekly_rows = db.execute(
        select(
            PilotEmployeeAssignment.week_start_date,
            func.coalesce(func.sum(PilotEmployeeAssignment.load_percent), 0),
            func.coalesce(func.sum(PilotEmployeeAssignment.hours), 0),
        )
        .where(PilotEmployeeAssignment.employee_id == employee_id)
        .group_by(PilotEmployeeAssignment.week_start_date)
        .order_by(PilotEmployeeAssignment.week_start_date.desc())
    ).all()

    weekly_loads = [
        EmployeeWeeklyLoad(
            week_start_date=row[0],
            total_load_percent=row[1],
            total_hours=row[2],
        )
        for row in weekly_rows
    ]

    selected_week_total = next(
        (item.total_load_percent for item in weekly_loads if item.week_start_date == selected_week),
        Decimal('0'),
    )

    return EmployeeDetail(
        id=employee.id,
        cas=employee.cas,
        full_name=employee.full_name,
        rc=employee.rc,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
        pilots=selected_week_pilots,
        weekly_loads=weekly_loads,
        selected_week_total_load_percent=selected_week_total,
        is_overloaded=selected_week_total > Decimal('100'),
    )


@router.get('/{employee_id}/pilots', response_model=list[EmployeePilotLoad])
def get_employee_pilots(
    employee_id: int,
    week_start_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[EmployeePilotLoad]:
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail='Employee not found')

    stmt = (
        select(
            Pilot.id,
            Pilot.name,
            PilotEmployeeAssignment.week_start_date,
            PilotEmployeeAssignment.load_percent,
            PilotEmployeeAssignment.hours,
            PilotEmployeeAssignment.pshe,
        )
        .join(Pilot, Pilot.id == PilotEmployeeAssignment.pilot_id)
        .where(PilotEmployeeAssignment.employee_id == employee_id)
        .order_by(PilotEmployeeAssignment.week_start_date.desc(), Pilot.name)
    )

    if week_start_date:
        stmt = stmt.where(PilotEmployeeAssignment.week_start_date == to_week_start(week_start_date))

    rows = db.execute(stmt).all()

    return [
        EmployeePilotLoad(
            pilot_id=row[0],
            pilot_name=row[1],
            week_start_date=row[2],
            load_percent=row[3],
            hours=row[4],
            pshe=row[5],
        )
        for row in rows
    ]
