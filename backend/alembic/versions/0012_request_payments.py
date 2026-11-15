"""Append-only confirmed CRM receipts and refunds, separate from commercial stages."""

import sqlalchemy as sa

from alembic import op

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_requests') as batch:
        batch.add_column(sa.Column('crm_request_id', sa.String(36), nullable=True))
        for column in ('qualified_at', 'proposal_sent_at', 'order_confirmed_at'):
            batch.add_column(sa.Column(column, sa.DateTime(timezone=True), nullable=True))
    op.create_table('site_request_payments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('site_request_id', sa.String(36), sa.ForeignKey('site_requests.id'), nullable=False),
        sa.Column('kind', sa.String(12), nullable=False),
        sa.Column('external_id', sa.String(64), nullable=False),
        sa.Column('payment_id', sa.String(64), nullable=False),
        sa.Column('amount', sa.Numeric(24, 8), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payload_hash', sa.String(64), nullable=False),
        sa.CheckConstraint("kind IN ('received', 'refunded')", name='ck_site_request_payment_kind'),
        sa.CheckConstraint('amount > 0', name='ck_site_request_payment_amount'),
        sa.UniqueConstraint('kind', 'external_id', name='uq_site_request_payment_external'),
        sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_site_request_payments_site_request_id', 'site_request_payments', ['site_request_id'])
    op.create_index('ix_site_request_payments_payment_id', 'site_request_payments', ['payment_id'])
    if op.get_bind().dialect.name == 'postgresql':
        op.execute("""CREATE OR REPLACE FUNCTION ogk_protect_request_payments() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Confirmed payment facts are append-only'
            USING ERRCODE = '23514'; RETURN NULL; END $$""")
        op.execute('CREATE TRIGGER protect_request_payments BEFORE UPDATE OR DELETE ON site_request_payments '
                   'FOR EACH ROW EXECUTE FUNCTION ogk_protect_request_payments()')
    elif op.get_bind().dialect.name == 'sqlite':
        for operation in ('UPDATE', 'DELETE'):
            op.execute(f'CREATE TRIGGER protect_request_payments_{operation.lower()} BEFORE {operation} '
                       "ON site_request_payments BEGIN SELECT RAISE(ABORT, 'Confirmed payment facts are append-only'); END")


def downgrade():
    op.drop_table('site_request_payments')
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP FUNCTION IF EXISTS ogk_protect_request_payments()')
    with op.batch_alter_table('site_requests') as batch:
        for column in ('order_confirmed_at', 'proposal_sent_at', 'qualified_at', 'crm_request_id'):
            batch.drop_column(column)
