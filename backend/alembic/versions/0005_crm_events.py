"""events from the CRM (flow F2) and what they report on site requests (F3)"""

import sqlalchemy as sa

from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('crm_events',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('type', sa.String(length=60), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('answer', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crm_events_type'), 'crm_events', ['type'], unique=False)
    op.create_index(op.f('ix_crm_events_received_at'), 'crm_events', ['received_at'], unique=False)
    with op.batch_alter_table('site_requests') as batch:
        batch.add_column(sa.Column('crm_status', sa.String(length=20), nullable=True))
        batch.add_column(sa.Column('crm_stage', sa.String(length=40), nullable=True))
        batch.add_column(sa.Column('crm_request_number', sa.String(length=40), nullable=True))
        batch.add_column(sa.Column('crm_updated_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('sale_amount', sa.Numeric(precision=18, scale=2), nullable=True))
        batch.add_column(sa.Column('sale_currency', sa.String(length=3), nullable=True))
    op.create_index('ix_products_crm_product_id', 'products', ['crm_product_id'], unique=False)


def downgrade():
    op.drop_index('ix_products_crm_product_id', table_name='products')
    with op.batch_alter_table('site_requests') as batch:
        for column in ('sale_currency', 'sale_amount', 'crm_updated_at', 'crm_request_number', 'crm_stage',
                       'crm_status'):
            batch.drop_column(column)
    op.drop_index(op.f('ix_crm_events_received_at'), table_name='crm_events')
    op.drop_index(op.f('ix_crm_events_type'), table_name='crm_events')
    op.drop_table('crm_events')
