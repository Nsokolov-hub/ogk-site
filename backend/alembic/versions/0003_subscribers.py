"""subscribers of the mailing (TZ 11.2, NFR-07)"""

import sqlalchemy as sa

from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('subscribers',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('lang', sa.String(length=2), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('source', sa.String(length=40), nullable=True),
    sa.Column('page_url', sa.String(length=2000), nullable=True),
    sa.Column('personal_data_consent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('marketing_consent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('client_ip', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('unsubscribe_token', sa.String(length=64), nullable=False),
    sa.Column('unsubscribed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('crm_synced_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("lang IN ('ru', 'en')"),
    sa.CheckConstraint("status IN ('active', 'unsubscribed')"),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('unsubscribe_token')
    )
    op.create_index(op.f('ix_subscribers_status'), 'subscribers', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_subscribers_status'), table_name='subscribers')
    op.drop_table('subscribers')
