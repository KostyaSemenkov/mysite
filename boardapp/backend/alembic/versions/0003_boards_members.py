"""boards and members

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'boards',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'board_members',
        sa.Column('board_id', sa.String(36),
                  sa.ForeignKey('boards.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(10), nullable=False),
        sa.UniqueConstraint('board_id', 'user_id'),
    )


def downgrade() -> None:
    op.drop_table('board_members')
    op.drop_table('boards')
