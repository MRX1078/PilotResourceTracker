"""initial schema

Revision ID: 20260426_0001
Revises: 
Create Date: 2026-04-26 00:00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260426_0001'
down_revision = None
branch_labels = None
depends_on = None


accounting_mode_enum = sa.Enum('MANUAL', 'SQL', name='accounting_mode_enum')
assignment_source_enum = sa.Enum('MANUAL', 'SQL', name='assignment_source_enum')
query_run_status_enum = sa.Enum('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', name='query_run_status_enum')


def upgrade() -> None:
    op.create_table(
        'pilots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('annual_revenue', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('accounting_mode', accounting_mode_enum, nullable=False, server_default='MANUAL'),
        sa.Column('sql_query', sa.Text(), nullable=True),
        sa.Column('additional_pshe_default', sa.Numeric(precision=8, scale=3), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pilots_id'), 'pilots', ['id'], unique=False)

    op.create_table(
        'employees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cas', sa.String(length=128), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('rc', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cas'),
        sa.UniqueConstraint('full_name', 'rc', name='uq_employees_full_name_rc'),
    )
    op.create_index(op.f('ix_employees_cas'), 'employees', ['cas'], unique=True)
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)

    op.create_table(
        'pilot_employee_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pilot_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('week_start_date', sa.Date(), nullable=False),
        sa.Column('load_percent', sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column('pshe', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('hours', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('source', assignment_source_enum, nullable=False, server_default='MANUAL'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pilot_id'], ['pilots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'pilot_id',
            'employee_id',
            'week_start_date',
            'source',
            name='uq_pilot_employee_week_source',
        ),
    )
    op.create_index(op.f('ix_pilot_employee_assignments_employee_id'), 'pilot_employee_assignments', ['employee_id'], unique=False)
    op.create_index(op.f('ix_pilot_employee_assignments_id'), 'pilot_employee_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_pilot_employee_assignments_pilot_id'), 'pilot_employee_assignments', ['pilot_id'], unique=False)
    op.create_index(op.f('ix_pilot_employee_assignments_week_start_date'), 'pilot_employee_assignments', ['week_start_date'], unique=False)

    op.create_table(
        'pilot_weekly_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pilot_id', sa.Integer(), nullable=False),
        sa.Column('week_start_date', sa.Date(), nullable=False),
        sa.Column('total_hours', sa.Numeric(precision=12, scale=3), nullable=False, server_default='0'),
        sa.Column('total_pshe', sa.Numeric(precision=12, scale=4), nullable=False, server_default='0'),
        sa.Column('additional_pshe', sa.Numeric(precision=10, scale=4), nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Numeric(precision=16, scale=2), nullable=False, server_default='0'),
        sa.Column('annual_revenue', sa.Numeric(precision=16, scale=2), nullable=False, server_default='0'),
        sa.Column('weekly_revenue_estimate', sa.Numeric(precision=16, scale=2), nullable=False, server_default='0'),
        sa.Column('profitability_estimate', sa.Numeric(precision=16, scale=2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['pilot_id'], ['pilots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pilot_id', 'week_start_date', name='uq_pilot_weekly_metrics_pilot_week'),
    )
    op.create_index(op.f('ix_pilot_weekly_metrics_id'), 'pilot_weekly_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_pilot_weekly_metrics_pilot_id'), 'pilot_weekly_metrics', ['pilot_id'], unique=False)
    op.create_index(op.f('ix_pilot_weekly_metrics_week_start_date'), 'pilot_weekly_metrics', ['week_start_date'], unique=False)

    op.create_table(
        'trino_query_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pilot_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', query_run_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('rows_returned', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['pilot_id'], ['pilots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trino_query_runs_id'), 'trino_query_runs', ['id'], unique=False)
    op.create_index(op.f('ix_trino_query_runs_pilot_id'), 'trino_query_runs', ['pilot_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trino_query_runs_pilot_id'), table_name='trino_query_runs')
    op.drop_index(op.f('ix_trino_query_runs_id'), table_name='trino_query_runs')
    op.drop_table('trino_query_runs')

    op.drop_index(op.f('ix_pilot_weekly_metrics_week_start_date'), table_name='pilot_weekly_metrics')
    op.drop_index(op.f('ix_pilot_weekly_metrics_pilot_id'), table_name='pilot_weekly_metrics')
    op.drop_index(op.f('ix_pilot_weekly_metrics_id'), table_name='pilot_weekly_metrics')
    op.drop_table('pilot_weekly_metrics')

    op.drop_index(op.f('ix_pilot_employee_assignments_week_start_date'), table_name='pilot_employee_assignments')
    op.drop_index(op.f('ix_pilot_employee_assignments_pilot_id'), table_name='pilot_employee_assignments')
    op.drop_index(op.f('ix_pilot_employee_assignments_id'), table_name='pilot_employee_assignments')
    op.drop_index(op.f('ix_pilot_employee_assignments_employee_id'), table_name='pilot_employee_assignments')
    op.drop_table('pilot_employee_assignments')

    op.drop_index(op.f('ix_employees_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_cas'), table_name='employees')
    op.drop_table('employees')

    op.drop_index(op.f('ix_pilots_id'), table_name='pilots')
    op.drop_table('pilots')
