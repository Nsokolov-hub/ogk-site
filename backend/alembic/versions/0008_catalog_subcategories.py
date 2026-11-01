"""Subcategories of the business's catalog «Каталог продукции по категориям» (31.10.2026): reagents, biochemistry,
chromatography and reference standards get the sections the import lays the assortment into
(app.catalog.importer.rules.FILE_CATEGORIES). Only the categories missing in the database are added, with the texts
of seed/catalog.json; existing ones and texts edited in the admin panel stay as they are. The catalog's root and the
home page stop offering equipment and laboratory containers (business remarks of 31.10.2026)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa

from alembic import op
from app.catalog.business_oct31 import clean

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

SEED = Path(__file__).resolve().parents[2] / 'seed' / 'catalog.json'
NEW = ('reagents/', 'biochemistry/', 'chromatography/', 'reference-standards/')

categories = sa.table('categories', sa.column('id', sa.String), sa.column('created_at', sa.DateTime(timezone=True)),
                      sa.column('version', sa.Integer), sa.column('parent_id', sa.String), sa.column('slug', sa.String),
                      sa.column('path', sa.String), sa.column('position', sa.Integer), sa.column('name_ru', sa.String),
                      sa.column('name_en', sa.String), sa.column('short_ru', sa.String),
                      sa.column('short_en', sa.String), sa.column('card_type', sa.String),
                      sa.column('facets', sa.JSON), sa.column('is_indexed', sa.Boolean),
                      sa.column('content', sa.JSON), sa.column('updated_at', sa.DateTime(timezone=True)))
pages = sa.table('content_pages', sa.column('id', sa.String), sa.column('content', sa.JSON),
                 sa.column('updated_at', sa.DateTime(timezone=True)))
settings = sa.table('catalog_settings', sa.column('key', sa.String), sa.column('value', sa.JSON))


def upgrade():
    db = op.get_bind()
    now = datetime.now(UTC)
    found = {row.path: row.id for row in db.execute(sa.select(categories.c.path, categories.c.id))}
    for raw in json.loads(SEED.read_text(encoding='utf-8'))['categories']:
        path, parent = raw['path'], raw.get('parent')
        # A subcategory whose parent is gone (removed by people) is not brought back.
        if path in found or not path.startswith(NEW) or parent not in found:
            continue
        category_id = str(uuid4())
        db.execute(categories.insert().values(
            id=category_id, created_at=now, version=1, parent_id=found[parent], slug=raw['slug'], path=path,
            position=raw['position'], name_ru=raw['nameRu'], name_en=raw.get('nameEn'), short_ru=raw.get('shortRu'),
            short_en=raw.get('shortEn'), card_type=raw['cardType'], facets=raw.get('facets') or [], is_indexed=True,
            content={key: value for key, value in (raw.get('content') or {}).items() if value}, updated_at=now))
        found[path] = category_id
    for row in db.execute(sa.select(pages.c.id, pages.c.content)).all():
        cleaned = clean(row.content)
        if cleaned != row.content:
            db.execute(pages.update().where(pages.c.id == row.id).values(content=cleaned, updated_at=now))
    root = db.execute(sa.select(settings.c.value).where(settings.c.key == 'catalog_root')).scalar()
    if isinstance(root, dict) and clean(root) != root:
        db.execute(settings.update().where(settings.c.key == 'catalog_root').values(value=clean(root)))


def downgrade():
    # The subcategories stay: their products would lose their category otherwise. Remove them in the admin panel.
    pass
