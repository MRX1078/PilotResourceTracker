"""add pilot-level trino connection overrides

Revision ID: 20260428_0002
Revises: 20260426_0001
Create Date: 2026-04-28 00:00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260428_0002'
down_revision = '20260426_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pilots', sa.Column('trino_host', sa.String(length=255), nullable=True))
    op.add_column('pilots', sa.Column('trino_port', sa.Integer(), nullable=True))
    op.add_column('pilots', sa.Column('trino_user', sa.String(length=255), nullable=True))
    op.add_column('pilots', sa.Column('trino_password', sa.String(length=512), nullable=True))
    op.add_column('pilots', sa.Column('trino_catalog', sa.String(length=255), nullable=True))
    op.add_column('pilots', sa.Column('trino_schema', sa.String(length=255), nullable=True))
    op.add_column('pilots', sa.Column('trino_http_scheme', sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column('pilots', 'trino_http_scheme')
    op.drop_column('pilots', 'trino_schema')
    op.drop_column('pilots', 'trino_catalog')
    op.drop_column('pilots', 'trino_password')
    op.drop_column('pilots', 'trino_user')
    op.drop_column('pilots', 'trino_port')
    op.drop_column('pilots', 'trino_host')
