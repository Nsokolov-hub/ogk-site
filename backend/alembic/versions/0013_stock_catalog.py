"""Stock freshness and frozen stock evidence on incoming requests."""

import json

import sqlalchemy as sa

from alembic import op

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('supplier_stock_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('competitor_offers', sa.Column('stock_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('site_request_items', sa.Column('site_packaging_id', sa.String(150), nullable=True))
    op.add_column('site_request_items', sa.Column('stock_snapshot', sa.JSON(), nullable=True))
    # Previous matching admitted brand prefixes and contradictory packs. Keep the observations for review,
    # but rebuild their links under the exact identity rules before displaying them as available.
    op.execute('UPDATE competitor_offers SET product_id = NULL, packaging_id = NULL '
               'WHERE product_id IS NOT NULL OR packaging_id IS NOT NULL')
    op.execute('UPDATE products SET supplier_stock = false, supplier_stock_until = NULL, needs_index = true '
               'WHERE supplier_stock = true')
    settings = sa.table('catalog_settings', sa.column('key', sa.String), sa.column('value', sa.JSON))
    connection = op.get_bind()
    for key in ('competitor_run', 'competitor_results', 'competitor_stock'):
        raw = connection.scalar(sa.select(settings.c.value).where(settings.c.key == key))
        value = json.loads(raw) if isinstance(raw, str) else raw
        if key == 'competitor_run':
            updated = None
        elif key == 'competitor_results':
            updated = {**(value or {}), 'finishedAt': None}
        elif isinstance(value, dict):
            updated = {**value, 'sources': list(dict.fromkeys([*(value.get('sources') or []),
                       'chimmed', 'skygen', 'diam', 'labteh', 'algimed', 'csdb', 'laverna',
                       'hplc', 'vilax', 'nevareaktiv', 'lenreactiv']))}
        else:
            continue
        if raw is not None:
            connection.execute(sa.update(settings).where(settings.c.key == key).values(value=updated))


def downgrade():
    op.drop_column('site_request_items', 'stock_snapshot')
    op.drop_column('site_request_items', 'site_packaging_id')
    op.drop_column('competitor_offers', 'stock_updated_at')
    op.drop_column('products', 'supplier_stock_until')
