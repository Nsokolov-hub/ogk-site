"""admin panel (TZ 13): staff and sessions, the journal of changes, pages and drafts, redirects, SEO landings,
demand of products, import uploads; trigram search of product names for the admin list"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('audit_entries',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actor_id', sa.String(length=36), nullable=True),
    sa.Column('actor_name', sa.String(length=200), nullable=False),
    sa.Column('entity', sa.String(length=40), nullable=False),
    sa.Column('entity_id', sa.String(length=200), nullable=False),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('summary', sa.String(length=300), nullable=False),
    sa.Column('before', sa.JSON(), nullable=True),
    sa.Column('after', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_entries_actor_id'), 'audit_entries', ['actor_id'], unique=False)
    op.create_index(op.f('ix_audit_entries_at'), 'audit_entries', ['at'], unique=False)
    op.create_index(op.f('ix_audit_entries_entity'), 'audit_entries', ['entity'], unique=False)
    op.create_index(op.f('ix_audit_entries_entity_id'), 'audit_entries', ['entity_id'], unique=False)
    op.create_table('content_pages',
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('content', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("status IN ('published', 'hidden')"),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('kind', 'slug')
    )
    op.create_index(op.f('ix_content_pages_kind'), 'content_pages', ['kind'], unique=False)
    op.create_table('drafts',
    sa.Column('entity', sa.String(length=30), nullable=False),
    sa.Column('entity_id', sa.String(length=36), nullable=False),
    sa.Column('data', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('publish_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('author_id', sa.String(length=36), nullable=True),
    sa.Column('author_name', sa.String(length=200), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entity', 'entity_id')
    )
    op.create_index(op.f('ix_drafts_publish_at'), 'drafts', ['publish_at'], unique=False)
    op.create_table('import_uploads',
    sa.Column('file_name', sa.String(length=300), nullable=False),
    sa.Column('storage_key', sa.String(length=200), nullable=False),
    sa.Column('size', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('header', sa.JSON(), nullable=False),
    sa.Column('sample', sa.JSON(), nullable=False),
    sa.Column('author_name', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('source', sa.String(length=60), nullable=True),
    sa.Column('dry_run', sa.Boolean(), nullable=False),
    sa.Column('batch_id', sa.String(length=36), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('storage_key')
    )
    op.create_table('redirects',
    sa.Column('source', sa.String(length=400), nullable=False),
    sa.Column('target', sa.String(length=500), nullable=False),
    sa.Column('code', sa.Integer(), nullable=False),
    sa.Column('note', sa.String(length=300), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint('code IN (301, 302)'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source')
    )
    op.create_table('seo_landings',
    sa.Column('category_path', sa.String(length=400), nullable=False),
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.Column('filters', sa.JSON(), nullable=False),
    sa.Column('content', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("status IN ('published', 'hidden')"),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('category_path', 'slug')
    )
    op.create_index(op.f('ix_seo_landings_category_path'), 'seo_landings', ['category_path'], unique=False)
    op.create_table('staff_users',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('totp_secret', sa.Text(), nullable=True),
    sa.Column('totp_enabled', sa.Boolean(), nullable=False),
    sa.Column('failed_logins', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("role IN ('admin', 'content', 'catalog', 'viewer')"),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('staff_sessions',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('csrf_token', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ip', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=300), nullable=True),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['staff_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_staff_sessions_user_id'), 'staff_sessions', ['user_id'], unique=False)
    op.create_table('product_demand',
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('views', sa.Integer(), nullable=False),
    sa.Column('requests', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('product_id', 'day')
    )
    op.create_index(op.f('ix_product_demand_day'), 'product_demand', ['day'], unique=False)
    if op.get_bind().dialect.name == 'postgresql':
        # «Название содержит…» in the admin list of 1.7 million products (TZ 12.1: pg_trgm).
        op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
        op.execute('CREATE INDEX IF NOT EXISTS ix_products_name_en_trgm ON products USING gin (name_en gin_trgm_ops)')


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP INDEX IF EXISTS ix_products_name_en_trgm')
    op.drop_index(op.f('ix_product_demand_day'), table_name='product_demand')
    op.drop_table('product_demand')
    op.drop_index(op.f('ix_staff_sessions_user_id'), table_name='staff_sessions')
    op.drop_table('staff_sessions')
    op.drop_table('staff_users')
    op.drop_index(op.f('ix_seo_landings_category_path'), table_name='seo_landings')
    op.drop_table('seo_landings')
    op.drop_table('redirects')
    op.drop_table('import_uploads')
    op.drop_index(op.f('ix_drafts_publish_at'), table_name='drafts')
    op.drop_table('drafts')
    op.drop_index(op.f('ix_content_pages_kind'), table_name='content_pages')
    op.drop_table('content_pages')
    op.drop_index(op.f('ix_audit_entries_entity_id'), table_name='audit_entries')
    op.drop_index(op.f('ix_audit_entries_entity'), table_name='audit_entries')
    op.drop_index(op.f('ix_audit_entries_at'), table_name='audit_entries')
    op.drop_index(op.f('ix_audit_entries_actor_id'), table_name='audit_entries')
    op.drop_table('audit_entries')
