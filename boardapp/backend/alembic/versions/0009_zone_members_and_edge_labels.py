"""Persist zone membership and arrow labels."""

import sqlalchemy as sa
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('tickets') as batch:
        batch.add_column(sa.Column('zone_id', sa.String(36), nullable=True))
        batch.create_foreign_key('fk_tickets_zone_id', 'zones', ['zone_id'], ['id'],
                                 ondelete='SET NULL')
        batch.create_index('ix_tickets_zone_id', ['zone_id'])
    op.add_column('edges', sa.Column('label', sa.String(100), nullable=False, server_default=''))

    # Recover the previous visual membership. Where zones overlap, the
    # smallest enclosing zone takes precedence, then the lowest id.
    tickets = sa.table('tickets', *(sa.column(c) for c in
                      ('board_id', 'zone_id', 'x', 'y', 'width', 'height')))
    zones = sa.table('zones', *(sa.column(c) for c in
                    ('id', 'board_id', 'x', 'y', 'width', 'height')))
    center_x = tickets.c.x + tickets.c.width / 2.0
    height = sa.case((tickets.c.height < 130, 130), else_=tickets.c.height)
    center_y = tickets.c.y + height / 2.0
    membership = sa.select(zones.c.id).where(
        zones.c.board_id == tickets.c.board_id,
        center_x.between(zones.c.x, zones.c.x + zones.c.width),
        center_y.between(zones.c.y, zones.c.y + zones.c.height),
    ).order_by(zones.c.width * zones.c.height, zones.c.id).limit(1).scalar_subquery()
    op.execute(tickets.update().values(zone_id=membership))


def downgrade() -> None:
    op.drop_column('edges', 'label')
    with op.batch_alter_table('tickets') as batch:
        batch.drop_index('ix_tickets_zone_id')
        batch.drop_constraint('fk_tickets_zone_id', type_='foreignkey')
        batch.drop_column('zone_id')
