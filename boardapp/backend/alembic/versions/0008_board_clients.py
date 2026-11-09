"""Track the last applied operation for each board editor session."""

import sqlalchemy as sa
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'board_clients',
        sa.Column('board_id', sa.String(36), sa.ForeignKey('boards.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('client_id', sa.String(36), primary_key=True),
        sa.Column('last_sequence', sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('board_clients')
