"""Stock of suppliers, 09.11.2026: positions in stock on chimmed-new.ru and klad.skygen.com (app.catalog.competitors).

Our products with the same brand and catalog number are shown «В наличии»; the flag is kept apart from
``availability``, which imports and managers set.
"""

import sqlalchemy as sa

from alembic import op

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('supplier_stock', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index('ix_products_supplier_stock', 'products', ['supplier_stock'], unique=False,
                    postgresql_where=sa.text('supplier_stock'), sqlite_where=sa.text('supplier_stock'))
    op.create_table(
        'competitor_offers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('external_id', sa.String(100), nullable=False),
        sa.Column('brand_name', sa.String(250), nullable=False),
        sa.Column('brand_id', sa.String(36), sa.ForeignKey('brands.id', ondelete='SET NULL')),
        sa.Column('catalog_number', sa.String(150), nullable=False),
        sa.Column('catalog_number_norm', sa.String(150), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('cas', sa.String(40)),
        sa.Column('pack', sa.String(120)),
        sa.Column('quantity', sa.Integer()),
        sa.Column('price', sa.String(60)),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='SET NULL')),
        sa.Column('packaging_id', sa.String(36)),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('source', 'external_id'),
    )
    for column in ('source', 'brand_id', 'catalog_number_norm', 'product_id', 'seen_at'):
        op.create_index(op.f(f'ix_competitor_offers_{column}'), 'competitor_offers', [column], unique=False)


def downgrade():
    for column in ('source', 'brand_id', 'catalog_number_norm', 'product_id', 'seen_at'):
        op.drop_index(op.f(f'ix_competitor_offers_{column}'), table_name='competitor_offers')
    op.drop_table('competitor_offers')
    op.drop_index('ix_products_supplier_stock', table_name='products')
    op.drop_column('products', 'supplier_stock')
