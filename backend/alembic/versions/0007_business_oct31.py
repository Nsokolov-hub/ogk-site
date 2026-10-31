"""Business remarks of 31 October 2026: equipment and glassware leave the catalog, the USP–NF Online subscription
is no longer sold. Their products go to the archive, the categories and their landings are removed, the old
addresses redirect, the texts of the pages stop offering them."""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op
from app.catalog.business_oct31 import NOT_SOLD, REDIRECTS, REMOVED_CATEGORIES, clean

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

categories = sa.table('categories', sa.column('id', sa.String), sa.column('path', sa.String),
                      sa.column('parent_id', sa.String))
product_categories = sa.table('product_categories', sa.column('product_id', sa.String),
                              sa.column('category_id', sa.String), sa.column('is_primary', sa.Boolean))
products = sa.table('products', sa.column('id', sa.String), sa.column('name_en', sa.String),
                    sa.column('status', sa.String), sa.column('needs_index', sa.Boolean),
                    sa.column('version', sa.Integer), sa.column('updated_at', sa.DateTime(timezone=True)))
landings = sa.table('seo_landings', sa.column('category_path', sa.String))
drafts = sa.table('drafts', sa.column('entity', sa.String), sa.column('entity_id', sa.String))
pages = sa.table('content_pages', sa.column('id', sa.String), sa.column('content', sa.JSON),
                 sa.column('updated_at', sa.DateTime(timezone=True)))
redirects = sa.table('redirects', sa.column('id', sa.String), sa.column('source', sa.String),
                     sa.column('target', sa.String), sa.column('code', sa.Integer), sa.column('note', sa.String),
                     sa.column('updated_at', sa.DateTime(timezone=True)),
                     sa.column('created_at', sa.DateTime(timezone=True)), sa.column('version', sa.Integer))
settings = sa.table('catalog_settings', sa.column('key', sa.String), sa.column('value', sa.JSON))


def archive(db, ids: set[str], now: datetime) -> None:
    for product_id in sorted(ids):
        db.execute(products.update().where(products.c.id == product_id, products.c.status != 'archived').values(
            status='archived', needs_index=True, version=products.c.version + 1, updated_at=now))


def upgrade():
    db = op.get_bind()
    now = datetime.now(UTC)
    removed = {row.id: row.path for row in db.execute(sa.select(categories.c.id, categories.c.path))
               if any(row.path == path or row.path.startswith(path + '/') for path in REMOVED_CATEGORIES)}
    if removed:
        linked = {row.product_id for row in db.execute(sa.select(product_categories.c.product_id).where(
            product_categories.c.category_id.in_(list(removed))))}
        elsewhere = {row.product_id for row in db.execute(sa.select(product_categories.c.product_id).where(
            product_categories.c.product_id.in_(list(linked)), product_categories.c.category_id.not_in(list(removed))))}
        # A product also placed in a category that stays keeps its card there.
        archive(db, linked - elsewhere, now)
        db.execute(product_categories.delete().where(product_categories.c.category_id.in_(list(removed))))
        db.execute(landings.delete().where(landings.c.category_path.in_(list(removed.values()))))
        db.execute(drafts.delete().where(drafts.c.entity == 'category', drafts.c.entity_id.in_(list(removed))))
        for category_id, _ in sorted(removed.items(), key=lambda item: -item[1].count('/')):
            db.execute(categories.delete().where(categories.c.id == category_id))
    subscriptions = {row.id for row in db.execute(sa.select(products.c.id, products.c.name_en).where(
        products.c.name_en.ilike('%nf%'))) if NOT_SOLD.search(row.name_en or '')}
    archive(db, subscriptions, now)
    known = {row.source for row in db.execute(sa.select(redirects.c.source))}
    for source, target in REDIRECTS.items():
        if source not in known:
            db.execute(redirects.insert().values(id=str(uuid4()), source=source, target=target, code=301,
                                                 note='Категория убрана из каталога 31.10.2026', updated_at=now,
                                                 created_at=now, version=1))
    for row in db.execute(sa.select(pages.c.id, pages.c.content)).all():
        content = row.content
        cleaned = clean(content)
        if cleaned != content:
            db.execute(pages.update().where(pages.c.id == row.id).values(content=cleaned, updated_at=now))
    feed = db.execute(sa.select(settings.c.value).where(settings.c.key == 'feed')).scalar()
    if isinstance(feed, dict) and isinstance(feed.get('categories'), list):
        kept = [path for path in feed['categories'] if path not in REMOVED_CATEGORIES]
        if kept != feed['categories']:
            db.execute(settings.update().where(settings.c.key == 'feed').values(value={**feed, 'categories': kept}))


def downgrade():
    # The categories come back with `python -m app.catalog.cli seed --content-only` of an older release; the archived
    # cards stay archived.
    pass
