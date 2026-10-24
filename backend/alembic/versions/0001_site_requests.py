"""site requests, delivery journal and outbox"""

import sqlalchemy as sa

from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('number_counters',
    sa.Column('key', sa.String(length=80), nullable=False),
    sa.Column('value', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('outbox_events',
    sa.Column('event_key', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_key')
    )
    op.create_index(op.f('ix_outbox_events_kind'), 'outbox_events', ['kind'], unique=False)
    op.create_index(op.f('ix_outbox_events_next_attempt_at'), 'outbox_events', ['next_attempt_at'], unique=False)
    op.create_index(op.f('ix_outbox_events_status'), 'outbox_events', ['status'], unique=False)
    op.create_table('rate_events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rate_events_created_at'), 'rate_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_rate_events_key'), 'rate_events', ['key'], unique=False)
    op.create_table('site_requests',
    sa.Column('number', sa.String(length=40), nullable=False),
    sa.Column('client_key', sa.String(length=64), nullable=False),
    sa.Column('payload_hash', sa.String(length=64), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('lang', sa.String(length=2), nullable=False),
    sa.Column('form_type', sa.String(length=40), nullable=True),
    sa.Column('page_url', sa.String(length=2000), nullable=True),
    sa.Column('customer_name', sa.String(length=200), nullable=False),
    sa.Column('company', sa.String(length=250), nullable=False),
    sa.Column('inn', sa.String(length=12), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('city', sa.String(length=200), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('desired_date', sa.Date(), nullable=True),
    sa.Column('marketing_consent', sa.Boolean(), nullable=False),
    sa.Column('consent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('client_ip', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('service', sa.JSON(), nullable=True),
    sa.Column('attribution', sa.JSON(), nullable=True),
    sa.Column('suspicious', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('crm_id', sa.String(length=36), nullable=True),
    sa.Column('crm_number', sa.String(length=40), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delivery_error', sa.String(length=80), nullable=True),
    sa.Column('alerted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("kind IN ('product_rfq', 'one_click', 'service', 'general')"),
    sa.CheckConstraint("lang IN ('ru', 'en')"),
    sa.CheckConstraint("status IN ('accepted', 'delivered', 'failed')"),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_key'),
    sa.UniqueConstraint('number')
    )
    op.create_index(op.f('ix_site_requests_status'), 'site_requests', ['status'], unique=False)
    op.create_table('delivery_attempts',
    sa.Column('request_id', sa.String(length=36), nullable=False),
    sa.Column('attempt', sa.Integer(), nullable=False),
    sa.Column('outcome', sa.String(length=20), nullable=False),
    sa.Column('status_code', sa.Integer(), nullable=True),
    sa.Column('error_code', sa.String(length=80), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['request_id'], ['site_requests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_attempts_request_id'), 'delivery_attempts', ['request_id'], unique=False)
    op.create_table('site_request_attachments',
    sa.Column('request_id', sa.String(length=36), nullable=False),
    sa.Column('file_name', sa.String(length=250), nullable=False),
    sa.Column('media_type', sa.String(length=100), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_key', sa.String(length=200), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['request_id'], ['site_requests.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('storage_key')
    )
    op.create_index(op.f('ix_site_request_attachments_request_id'), 'site_request_attachments', ['request_id'], unique=False)
    op.create_table('site_request_items',
    sa.Column('request_id', sa.String(length=36), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('site_product_id', sa.String(length=100), nullable=True),
    sa.Column('brand', sa.String(length=200), nullable=True),
    sa.Column('catalog_number', sa.String(length=150), nullable=True),
    sa.Column('cas', sa.String(length=30), nullable=True),
    sa.Column('name', sa.String(length=500), nullable=False),
    sa.Column('packaging', sa.String(length=200), nullable=True),
    sa.Column('quantity', sa.Numeric(precision=24, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('analogue', sa.String(length=20), nullable=False),
    sa.Column('custom_packaging', sa.Boolean(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('page_url', sa.String(length=2000), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("analogue IN ('none', 'allowed', 'requested')"),
    sa.CheckConstraint('quantity > 0'),
    sa.ForeignKeyConstraint(['request_id'], ['site_requests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_site_request_items_request_id'), 'site_request_items', ['request_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_site_request_items_request_id'), table_name='site_request_items')
    op.drop_table('site_request_items')
    op.drop_index(op.f('ix_site_request_attachments_request_id'), table_name='site_request_attachments')
    op.drop_table('site_request_attachments')
    op.drop_index(op.f('ix_delivery_attempts_request_id'), table_name='delivery_attempts')
    op.drop_table('delivery_attempts')
    op.drop_index(op.f('ix_site_requests_status'), table_name='site_requests')
    op.drop_table('site_requests')
    op.drop_index(op.f('ix_rate_events_key'), table_name='rate_events')
    op.drop_index(op.f('ix_rate_events_created_at'), table_name='rate_events')
    op.drop_table('rate_events')
    op.drop_index(op.f('ix_outbox_events_status'), table_name='outbox_events')
    op.drop_index(op.f('ix_outbox_events_next_attempt_at'), table_name='outbox_events')
    op.drop_index(op.f('ix_outbox_events_kind'), table_name='outbox_events')
    op.drop_table('outbox_events')
    op.drop_table('number_counters')
