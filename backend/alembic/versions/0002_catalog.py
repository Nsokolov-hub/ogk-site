"""catalog: brands, categories, substances, products, imports, search journal, carts (TZ 5.1, 6, 9.5, RFQ-01)"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('brands',
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('logo', sa.String(length=300), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('is_partner', sa.Boolean(), nullable=False),
    sa.Column('custom_packaging', sa.Boolean(), nullable=False),
    sa.Column('page_published', sa.Boolean(), nullable=False),
    sa.Column('wave', sa.Integer(), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('crm_manufacturer_id', sa.String(length=36), nullable=True),
    sa.Column('merged_into_id', sa.String(length=36), nullable=True),
    sa.Column('content', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['merged_into_id'], ['brands.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('crm_manufacturer_id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('carts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('items', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_carts_updated_at'), 'carts', ['updated_at'], unique=False)
    op.create_table('catalog_settings',
    sa.Column('key', sa.String(length=80), nullable=False),
    sa.Column('value', sa.JSON(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('categories',
    sa.Column('parent_id', sa.String(length=36), nullable=True),
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.Column('path', sa.String(length=400), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('name_ru', sa.String(length=200), nullable=False),
    sa.Column('name_en', sa.String(length=200), nullable=True),
    sa.Column('short_ru', sa.String(length=100), nullable=True),
    sa.Column('short_en', sa.String(length=100), nullable=True),
    sa.Column('card_type', sa.String(length=20), nullable=False),
    sa.Column('facets', sa.JSON(), nullable=False),
    sa.Column('is_indexed', sa.Boolean(), nullable=False),
    sa.Column('content', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('path')
    )
    op.create_index(op.f('ix_categories_parent_id'), 'categories', ['parent_id'], unique=False)
    op.create_table('controlled_register',
    sa.Column('list', sa.String(length=10), nullable=False),
    sa.Column('name', sa.String(length=500), nullable=False),
    sa.Column('cas', sa.JSON(), nullable=False),
    sa.Column('names', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('import_sources',
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('mapping', sa.JSON(), nullable=False),
    sa.Column('options', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('search_misses',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('query', sa.String(length=200), nullable=False),
    sa.Column('lang', sa.String(length=2), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.Column('first_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('query', 'lang')
    )
    op.create_index(op.f('ix_search_misses_last_at'), 'search_misses', ['last_at'], unique=False)
    op.create_table('slug_redirects',
    sa.Column('entity', sa.String(length=20), nullable=False),
    sa.Column('old_slug', sa.String(length=400), nullable=False),
    sa.Column('target_id', sa.String(length=36), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entity', 'old_slug')
    )
    op.create_index(op.f('ix_slug_redirects_target_id'), 'slug_redirects', ['target_id'], unique=False)
    op.create_table('substances',
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.Column('name_ru', sa.String(length=250), nullable=False),
    sa.Column('name_en', sa.String(length=250), nullable=False),
    sa.Column('cas', sa.String(length=20), nullable=True),
    sa.Column('formula', sa.String(length=200), nullable=True),
    sa.Column('molecular_weight', sa.String(length=40), nullable=True),
    sa.Column('synonyms', sa.JSON(), nullable=False),
    sa.Column('content', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_substances_cas'), 'substances', ['cas'], unique=False)
    op.create_table('brand_aliases',
    sa.Column('brand_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=250), nullable=False),
    sa.Column('normalized', sa.String(length=250), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('normalized')
    )
    op.create_index(op.f('ix_brand_aliases_brand_id'), 'brand_aliases', ['brand_id'], unique=False)
    op.create_table('import_batches',
    sa.Column('source_id', sa.String(length=36), nullable=False),
    sa.Column('file_name', sa.String(length=300), nullable=False),
    sa.Column('file_sha256', sa.String(length=64), nullable=False),
    sa.Column('dry_run', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('rows_total', sa.Integer(), nullable=False),
    sa.Column('rows_done', sa.Integer(), nullable=False),
    sa.Column('counters', sa.JSON(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('author', sa.String(length=100), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['import_sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_batches_source_id'), 'import_batches', ['source_id'], unique=False)
    op.create_index(op.f('ix_import_batches_status'), 'import_batches', ['status'], unique=False)
    op.create_table('import_issues',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('batch_id', sa.String(length=36), nullable=False),
    sa.Column('row_number', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('values', sa.JSON(), nullable=False),
    sa.Column('product_id', sa.String(length=36), nullable=True),
    sa.Column('resolved', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batches.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_issues_batch_id'), 'import_issues', ['batch_id'], unique=False)
    op.create_index(op.f('ix_import_issues_kind'), 'import_issues', ['kind'], unique=False)
    op.create_table('products',
    sa.Column('card_type', sa.String(length=20), nullable=False),
    sa.Column('brand_id', sa.String(length=36), nullable=False),
    sa.Column('catalog_number', sa.String(length=150), nullable=False),
    sa.Column('catalog_number_norm', sa.String(length=150), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('name_en', sa.String(length=500), nullable=False),
    sa.Column('name_ru', sa.String(length=500), nullable=True),
    sa.Column('source_name', sa.String(length=500), nullable=True),
    sa.Column('synonyms', sa.JSON(), nullable=False),
    sa.Column('cas', sa.String(length=20), nullable=True),
    sa.Column('alt_cas', sa.JSON(), nullable=False),
    sa.Column('substance_id', sa.String(length=36), nullable=True),
    sa.Column('substance_role', sa.String(length=20), nullable=True),
    sa.Column('attributes', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('formula', sa.String(length=200), nullable=True),
    sa.Column('formula_hill', sa.String(length=200), nullable=True),
    sa.Column('molecular_weight', sa.String(length=40), nullable=True),
    sa.Column('smiles', sa.Text(), nullable=True),
    sa.Column('iupac_name', sa.Text(), nullable=True),
    sa.Column('purity', sa.String(length=200), nullable=True),
    sa.Column('storage', sa.String(length=20), nullable=True),
    sa.Column('shipping', sa.String(length=20), nullable=True),
    sa.Column('dangerous_goods', sa.Boolean(), nullable=True),
    sa.Column('texts', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('unique_description', sa.Boolean(), nullable=False),
    sa.Column('images', sa.JSON(), nullable=False),
    sa.Column('availability', sa.String(length=20), nullable=False),
    sa.Column('custom_packaging', sa.Boolean(), nullable=True),
    sa.Column('discontinued', sa.Boolean(), nullable=False),
    sa.Column('controlled', sa.String(length=10), nullable=True),
    sa.Column('controlled_state', sa.String(length=20), nullable=True),
    sa.Column('source', sa.String(length=60), nullable=False),
    sa.Column('created_batch_id', sa.String(length=36), nullable=True),
    sa.Column('last_import_run', sa.String(length=36), nullable=True),
    sa.Column('crm_product_id', sa.String(length=36), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('completeness', sa.Integer(), nullable=False),
    sa.Column('index_override', sa.Boolean(), nullable=True),
    sa.Column('indexable', sa.Boolean(), nullable=False),
    sa.Column('seo', sa.JSON(), nullable=False),
    sa.Column('popularity', sa.Integer(), nullable=False),
    sa.Column('manual_fields', sa.JSON(), nullable=False),
    sa.Column('needs_index', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
    sa.ForeignKeyConstraint(['created_batch_id'], ['import_batches.id'], ),
    sa.ForeignKeyConstraint(['substance_id'], ['substances.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('brand_id', 'catalog_number_norm'),
    sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_products_brand_id'), 'products', ['brand_id'], unique=False)
    op.create_index(op.f('ix_products_cas'), 'products', ['cas'], unique=False)
    op.create_index(op.f('ix_products_catalog_number_norm'), 'products', ['catalog_number_norm'], unique=False)
    op.create_index(op.f('ix_products_created_batch_id'), 'products', ['created_batch_id'], unique=False)
    op.create_index(op.f('ix_products_formula_hill'), 'products', ['formula_hill'], unique=False)
    op.create_index(op.f('ix_products_indexable'), 'products', ['indexable'], unique=False)
    op.create_index('ix_products_needs_index', 'products', ['needs_index'], unique=False, postgresql_where=sa.text('needs_index'), sqlite_where=sa.text('needs_index'))
    op.create_index(op.f('ix_products_status'), 'products', ['status'], unique=False)
    op.create_index(op.f('ix_products_substance_id'), 'products', ['substance_id'], unique=False)
    op.create_table('documents',
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=30), nullable=False),
    sa.Column('lang', sa.String(length=2), nullable=False),
    sa.Column('title_ru', sa.String(length=250), nullable=True),
    sa.Column('title_en', sa.String(length=250), nullable=True),
    sa.Column('href', sa.String(length=500), nullable=True),
    sa.Column('access', sa.String(length=20), nullable=False),
    sa.Column('rights_basis', sa.Text(), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_product_id'), 'documents', ['product_id'], unique=False)
    op.create_table('import_changes',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('batch_id', sa.String(length=36), nullable=False),
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('before', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batches.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_changes_batch_id'), 'import_changes', ['batch_id'], unique=False)
    op.create_index(op.f('ix_import_changes_product_id'), 'import_changes', ['product_id'], unique=False)
    op.create_table('packagings',
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=80), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=6), nullable=True),
    sa.Column('unit', sa.String(length=10), nullable=True),
    sa.Column('label_ru', sa.String(length=120), nullable=False),
    sa.Column('label_en', sa.String(length=120), nullable=False),
    sa.Column('catalog_number', sa.String(length=150), nullable=True),
    sa.Column('catalog_number_norm', sa.String(length=150), nullable=True),
    sa.Column('availability', sa.String(length=20), nullable=False),
    sa.Column('price_estimate', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('crm_packing_id', sa.String(length=36), nullable=True),
    sa.Column('created_batch_id', sa.String(length=36), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('product_id', 'key')
    )
    op.create_index(op.f('ix_packagings_catalog_number_norm'), 'packagings', ['catalog_number_norm'], unique=False)
    op.create_index(op.f('ix_packagings_created_batch_id'), 'packagings', ['created_batch_id'], unique=False)
    op.create_index(op.f('ix_packagings_key'), 'packagings', ['key'], unique=False)
    op.create_index(op.f('ix_packagings_product_id'), 'packagings', ['product_id'], unique=False)
    op.create_table('product_categories',
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('category_id', sa.String(length=36), nullable=False),
    sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('product_id', 'category_id')
    )
    op.create_index(op.f('ix_product_categories_category_id'), 'product_categories', ['category_id'], unique=False)
    op.create_table('product_relations',
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('related_id', sa.String(length=36), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['related_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('product_id', 'related_id', 'kind')
    )


def downgrade():
    op.drop_table('product_relations')
    op.drop_index(op.f('ix_product_categories_category_id'), table_name='product_categories')
    op.drop_table('product_categories')
    op.drop_index(op.f('ix_packagings_product_id'), table_name='packagings')
    op.drop_index(op.f('ix_packagings_key'), table_name='packagings')
    op.drop_index(op.f('ix_packagings_created_batch_id'), table_name='packagings')
    op.drop_index(op.f('ix_packagings_catalog_number_norm'), table_name='packagings')
    op.drop_table('packagings')
    op.drop_index(op.f('ix_import_changes_product_id'), table_name='import_changes')
    op.drop_index(op.f('ix_import_changes_batch_id'), table_name='import_changes')
    op.drop_table('import_changes')
    op.drop_index(op.f('ix_documents_product_id'), table_name='documents')
    op.drop_table('documents')
    op.drop_index(op.f('ix_products_substance_id'), table_name='products')
    op.drop_index(op.f('ix_products_status'), table_name='products')
    op.drop_index('ix_products_needs_index', table_name='products', postgresql_where=sa.text('needs_index'), sqlite_where=sa.text('needs_index'))
    op.drop_index(op.f('ix_products_indexable'), table_name='products')
    op.drop_index(op.f('ix_products_formula_hill'), table_name='products')
    op.drop_index(op.f('ix_products_created_batch_id'), table_name='products')
    op.drop_index(op.f('ix_products_catalog_number_norm'), table_name='products')
    op.drop_index(op.f('ix_products_cas'), table_name='products')
    op.drop_index(op.f('ix_products_brand_id'), table_name='products')
    op.drop_table('products')
    op.drop_index(op.f('ix_import_issues_kind'), table_name='import_issues')
    op.drop_index(op.f('ix_import_issues_batch_id'), table_name='import_issues')
    op.drop_table('import_issues')
    op.drop_index(op.f('ix_import_batches_status'), table_name='import_batches')
    op.drop_index(op.f('ix_import_batches_source_id'), table_name='import_batches')
    op.drop_table('import_batches')
    op.drop_index(op.f('ix_brand_aliases_brand_id'), table_name='brand_aliases')
    op.drop_table('brand_aliases')
    op.drop_index(op.f('ix_substances_cas'), table_name='substances')
    op.drop_table('substances')
    op.drop_index(op.f('ix_slug_redirects_target_id'), table_name='slug_redirects')
    op.drop_table('slug_redirects')
    op.drop_index(op.f('ix_search_misses_last_at'), table_name='search_misses')
    op.drop_table('search_misses')
    op.drop_table('import_sources')
    op.drop_table('controlled_register')
    op.drop_index(op.f('ix_categories_parent_id'), table_name='categories')
    op.drop_table('categories')
    op.drop_table('catalog_settings')
    op.drop_index(op.f('ix_carts_updated_at'), table_name='carts')
    op.drop_table('carts')
    op.drop_table('brands')
