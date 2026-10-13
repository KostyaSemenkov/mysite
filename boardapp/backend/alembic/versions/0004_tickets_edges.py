"""tickets and edges

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tickets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('board_id', sa.String(36),
                  sa.ForeignKey('boards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('width', sa.Float(), nullable=False),
        sa.Column('height', sa.Float(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('color', sa.String(9), nullable=False),
        sa.Column('updated_by', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'edges',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('board_id', sa.String(36),
                  sa.ForeignKey('boards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_ticket_id', sa.String(36),
                  sa.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_ticket_id', sa.String(36),
                  sa.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('updated_by', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('edges')
    op.drop_table('tickets')
