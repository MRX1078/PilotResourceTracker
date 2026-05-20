"""replace per-pilot trino connection with global app_settings

Revision ID: 20260520_0003
Revises: 20260428_0002
Create Date: 2026-05-20 00:00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260520_0003'
down_revision = '20260428_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trino_host', sa.String(length=255), nullable=True),
        sa.Column('trino_port', sa.Integer(), nullable=True),
        sa.Column('trino_user', sa.String(length=255), nullable=True),
        sa.Column('trino_password', sa.String(length=512), nullable=True),
        sa.Column('trino_catalog', sa.String(length=255), nullable=True),
        sa.Column('trino_schema', sa.String(length=255), nullable=True),
        sa.Column('trino_http_scheme', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Seed the singleton row, pulling values from any pilot that already has
    # them filled in (best-effort migration of per-pilot overrides into the
    # new global setting). If there are no pilots or all overrides are NULL,
    # all fields just stay NULL and the user fills them in on the Backups page.
    op.execute(
        """
        INSERT INTO app_settings (
            id, trino_host, trino_port, trino_user, trino_password,
            trino_catalog, trino_schema, trino_http_scheme
        ) VALUES (
            1,
            (SELECT trino_host FROM pilots WHERE trino_host IS NOT NULL LIMIT 1),
            (SELECT trino_port FROM pilots WHERE trino_port IS NOT NULL LIMIT 1),
            (SELECT trino_user FROM pilots WHERE trino_user IS NOT NULL LIMIT 1),
            (SELECT trino_password FROM pilots WHERE trino_password IS NOT NULL LIMIT 1),
            (SELECT trino_catalog FROM pilots WHERE trino_catalog IS NOT NULL LIMIT 1),
            (SELECT trino_schema FROM pilots WHERE trino_schema IS NOT NULL LIMIT 1),
            (SELECT trino_http_scheme FROM pilots WHERE trino_http_scheme IS NOT NULL LIMIT 1)
        )
        """
    )

    op.drop_column('pilots', 'trino_http_scheme')
    op.drop_column('pilots', 'trino_schema')
    op.drop_column('pilots', 'trino_catalog')
    op.drop_column('pilots', 'trino_password')
    op.drop_column('pilots', 'trino_user')
    op.drop_column('pilots', 'trino_port')
    op.drop_column('pilots', 'trino_host')


def downgrade() -> None:
    op.add_column('pilots', sa.Column('trino_host', sa.String(length=255), nullable=True))
    op.add_column('pilots', sa.Column('trino_port', sa.Integer(), nullable=True))
    op.add_column('pilots', sa.Column('trino_user', sa.String(length=255), nullable=True))
    op.add_column('pilots', sa.Column('trino_password', sa.String(length=512), nullable=True))
    op.add_column('pilots', sa.Column('trino_catalog', sa.String(length=255), nullable=True))
    op.add_column('pilots', sa.Column('trino_schema', sa.String(length=255), nullable=True))
    op.add_column('pilots', sa.Column('trino_http_scheme', sa.String(length=16), nullable=True))

    # Best-effort: copy back to all existing pilots so SQL refresh keeps working.
    op.execute(
        """
        UPDATE pilots SET
            trino_host = (SELECT trino_host FROM app_settings WHERE id = 1),
            trino_port = (SELECT trino_port FROM app_settings WHERE id = 1),
            trino_user = (SELECT trino_user FROM app_settings WHERE id = 1),
            trino_password = (SELECT trino_password FROM app_settings WHERE id = 1),
            trino_catalog = (SELECT trino_catalog FROM app_settings WHERE id = 1),
            trino_schema = (SELECT trino_schema FROM app_settings WHERE id = 1),
            trino_http_scheme = (SELECT trino_http_scheme FROM app_settings WHERE id = 1)
        """
    )

    op.drop_table('app_settings')
