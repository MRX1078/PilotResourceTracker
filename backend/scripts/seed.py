from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete

from app.database import SessionLocal
from app.models.assignment import PilotEmployeeAssignment
from app.models.employee import Employee
from app.models.enums import AccountingMode, AssignmentSource, QueryRunStatus
from app.models.pilot import Pilot
from app.models.pilot_weekly_metric import PilotWeeklyMetric
from app.models.trino_query_run import TrinoQueryRun
from app.services.metrics_service import normalize_assignment_values, recompute_pilot_metrics


def week_monday(offset_weeks: int) -> date:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(weeks=offset_weeks)


def run_seed() -> None:
    session = SessionLocal()
    try:
        session.execute(delete(TrinoQueryRun))
        session.execute(delete(PilotWeeklyMetric))
        session.execute(delete(PilotEmployeeAssignment))
        session.execute(delete(Employee))
        session.execute(delete(Pilot))
        session.commit()

        employees_data = [
            {'cas': 'cas101', 'full_name': 'Иванов Иван', 'rc': 'RC-1'},
            {'cas': 'cas102', 'full_name': 'Петров Петр', 'rc': 'RC-1'},
            {'cas': 'cas103', 'full_name': 'Сидорова Анна', 'rc': 'RC-2'},
            {'cas': 'cas104', 'full_name': 'Орлов Дмитрий', 'rc': 'RC-2'},
            {'cas': 'cas105', 'full_name': 'Кузнецова Мария', 'rc': 'RC-3'},
            {'cas': 'cas106', 'full_name': 'Волков Алексей', 'rc': 'RC-3'},
            {'cas': 'cas107', 'full_name': 'Смирнова Ольга', 'rc': 'RC-1'},
            {'cas': 'cas108', 'full_name': 'Федоров Павел', 'rc': 'RC-2'},
            {'cas': 'cas109', 'full_name': 'Зайцева Елена', 'rc': 'RC-3'},
            {'cas': 'cas110', 'full_name': 'Никитин Сергей', 'rc': 'RC-1'},
            {'cas': 'cas111', 'full_name': 'Егорова Дарья', 'rc': 'RC-2'},
            {'cas': 'cas112', 'full_name': 'Алексеев Роман', 'rc': 'RC-3'},
        ]

        employees = [Employee(**item) for item in employees_data]
        session.add_all(employees)
        session.flush()

        pilots = [
            Pilot(
                name='Pilot Atlas',
                description='Ручной пилот для аналитики загрузки команды DataOps.',
                annual_revenue=Decimal('45000000'),
                accounting_mode=AccountingMode.MANUAL,
                additional_pshe_default=Decimal('0.3'),
                is_active=True,
            ),
            Pilot(
                name='Pilot Borealis',
                description='Ручной пилот оптимизации клиентских процессов.',
                annual_revenue=Decimal('38000000'),
                accounting_mode=AccountingMode.MANUAL,
                additional_pshe_default=Decimal('0.1'),
                is_active=True,
            ),
            Pilot(
                name='Pilot Cobalt SQL',
                description='SQL-пилот, данные подтягиваются из Trino.',
                annual_revenue=Decimal('52000000'),
                accounting_mode=AccountingMode.SQL,
                sql_query=(
                    "SELECT\n"
                    "    date_trunc('week', event_date) AS week_start_date,\n"
                    "    cas,\n"
                    "    full_name,\n"
                    "    rc,\n"
                    "    SUM(hours_spent) AS hours,\n"
                    "    SUM(hours_spent) / 40.0 * 100 AS load_percent\n"
                    "FROM some_schema.some_table\n"
                    "WHERE pilot_name = 'Pilot Cobalt SQL'\n"
                    "GROUP BY 1, 2, 3, 4"
                ),
                additional_pshe_default=Decimal('0.0'),
                is_active=True,
            ),
            Pilot(
                name='Pilot Delta',
                description='Пилот с экспертизой в ML и ручным учетом.',
                annual_revenue=Decimal('27000000'),
                accounting_mode=AccountingMode.MANUAL,
                additional_pshe_default=Decimal('0.2'),
                is_active=True,
            ),
            Pilot(
                name='Pilot Echo',
                description='Дополнительный активный пилот для кросс-нагрузки.',
                annual_revenue=Decimal('30000000'),
                accounting_mode=AccountingMode.MANUAL,
                additional_pshe_default=Decimal('0.0'),
                is_active=True,
            ),
        ]

        session.add_all(pilots)
        session.flush()

        work_hours = Decimal('40')

        def add_assignment(
            pilot: Pilot,
            employee: Employee,
            week_start_date: date,
            hours: Decimal,
            source: AssignmentSource = AssignmentSource.MANUAL,
        ) -> None:
            normalized_hours, normalized_pshe, normalized_load = normalize_assignment_values(
                hours=hours,
                pshe=None,
                load_percent=None,
                work_hours_per_week=work_hours,
            )
            session.add(
                PilotEmployeeAssignment(
                    pilot_id=pilot.id,
                    employee_id=employee.id,
                    week_start_date=week_start_date,
                    hours=normalized_hours,
                    pshe=normalized_pshe,
                    load_percent=normalized_load,
                    source=source,
                )
            )

        weeks = [week_monday(offset) for offset in (3, 2, 1, 0)]

        add_assignment(pilots[0], employees[0], weeks[0], Decimal('32'))
        add_assignment(pilots[0], employees[1], weeks[0], Decimal('24'))
        add_assignment(pilots[0], employees[2], weeks[0], Decimal('20'))
        add_assignment(pilots[0], employees[0], weeks[1], Decimal('28'))
        add_assignment(pilots[0], employees[3], weeks[1], Decimal('18'))
        add_assignment(pilots[0], employees[4], weeks[1], Decimal('22'))
        add_assignment(pilots[0], employees[5], weeks[2], Decimal('25'))
        add_assignment(pilots[0], employees[6], weeks[2], Decimal('16'))
        add_assignment(pilots[0], employees[2], weeks[3], Decimal('20'))

        add_assignment(pilots[1], employees[0], weeks[0], Decimal('15'))
        add_assignment(pilots[1], employees[7], weeks[0], Decimal('25'))
        add_assignment(pilots[1], employees[8], weeks[1], Decimal('30'))
        add_assignment(pilots[1], employees[2], weeks[1], Decimal('10'))
        add_assignment(pilots[1], employees[9], weeks[2], Decimal('35'))
        add_assignment(pilots[1], employees[10], weeks[3], Decimal('18'))

        add_assignment(pilots[2], employees[1], weeks[0], Decimal('12'), source=AssignmentSource.SQL)
        add_assignment(pilots[2], employees[3], weeks[0], Decimal('20'), source=AssignmentSource.SQL)
        add_assignment(pilots[2], employees[4], weeks[1], Decimal('34'), source=AssignmentSource.SQL)
        add_assignment(pilots[2], employees[11], weeks[2], Decimal('26'), source=AssignmentSource.SQL)

        add_assignment(pilots[3], employees[5], weeks[0], Decimal('20'))
        add_assignment(pilots[3], employees[6], weeks[0], Decimal('24'))
        add_assignment(pilots[3], employees[7], weeks[1], Decimal('15'))
        add_assignment(pilots[3], employees[8], weeks[2], Decimal('18'))
        add_assignment(pilots[3], employees[0], weeks[3], Decimal('12'))

        add_assignment(pilots[4], employees[0], weeks[0], Decimal('8'))
        add_assignment(pilots[4], employees[2], weeks[0], Decimal('10'))
        add_assignment(pilots[4], employees[10], weeks[1], Decimal('22'))
        add_assignment(pilots[4], employees[1], weeks[2], Decimal('14'))

        session.flush()

        for pilot in pilots:
            recompute_pilot_metrics(session, pilot.id)

        session.add_all(
            [
                TrinoQueryRun(
                    pilot_id=pilots[2].id,
                    started_at=datetime.utcnow() - timedelta(days=2),
                    finished_at=datetime.utcnow() - timedelta(days=2, minutes=-1),
                    status=QueryRunStatus.SUCCESS,
                    error_message=None,
                    rows_returned=4,
                ),
                TrinoQueryRun(
                    pilot_id=pilots[2].id,
                    started_at=datetime.utcnow() - timedelta(days=1),
                    finished_at=datetime.utcnow() - timedelta(days=1, minutes=-1),
                    status=QueryRunStatus.FAILED,
                    error_message='Trino cluster temporary unavailable',
                    rows_returned=0,
                ),
            ]
        )

        session.commit()
        print('Seed completed: pilots=5 employees=12 assignments inserted.')
    finally:
        session.close()


if __name__ == '__main__':
    run_seed()
