"""user external_id for site SSO

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('external_id', sa.String(64), nullable=True))
    op.create_index('ix_users_external_id', 'users', ['external_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_external_id', table_name='users')
    op.drop_column('users', 'external_id')
