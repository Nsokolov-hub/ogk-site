"""The catalog structure and the test catalog (backend/seed/catalog.json).

``--content-only`` loads what production needs before the first import: the category tree with its texts, brand
pages and substances. The full load adds 413 test products for development and staging and is refused in
production.

Loading is idempotent: brands, categories and substances are matched by slug or path, products by brand and
normalized catalog number, so a second run updates rows instead of duplicating them.
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.catalog import controlled
from app.catalog.models import (
    Brand,
    BrandAlias,
    Category,
    Document,
    Packaging,
    Product,
    ProductCategory,
    Substance,
)
from app.catalog.normalize import brand_key, cas_or_none, compact, hill_key, parse_pack
from app.catalog.service import refresh_card
from app.catalog.settings import get_setting, set_setting
from app.core.db import utcnow

SEED_FILE = Path(__file__).resolve().parents[2] / 'seed' / 'catalog.json'
CONTENT_FILE = Path(__file__).resolve().parents[2] / 'seed' / 'content.json'


def _brands(db: Session, rows: list[dict[str, Any]]) -> dict[str, Brand]:
    found = {brand.slug: brand for brand in db.scalars(select(Brand))}
    for position, raw in enumerate(rows):
        brand = found.get(raw['slug']) or Brand(slug=raw['slug'])
        brand.position = position
        brand.name, brand.logo, brand.country = raw['name'], raw.get('logo'), raw.get('country')
        brand.custom_packaging, brand.wave = bool(raw.get('customPackaging')), raw.get('wave')
        brand.page_published, brand.content = bool(raw.get('pagePublished')), raw.get('content') or {}
        db.add(brand)
        found[brand.slug] = brand
    db.flush()
    for brand in found.values():
        for spelling in {brand.name, brand.slug}:
            key = brand_key(spelling)
            if key and db.scalar(select(BrandAlias.id).where(BrandAlias.normalized == key)) is None:
                db.add(BrandAlias(brand_id=brand.id, name=spelling, normalized=key, source='seed'))
                db.flush()
    return found


def _categories(db: Session, rows: list[dict[str, Any]], root: dict[str, Any]) -> dict[str, Category]:
    found = {category.path: category for category in db.scalars(select(Category))}
    for raw in rows:
        category = found.get(raw['path']) or Category(path=raw['path'])
        category.slug, category.position = raw['slug'], raw['position']
        category.parent_id = found[raw['parent']].id if raw.get('parent') else None
        category.name_ru, category.name_en = raw['nameRu'], raw.get('nameEn')
        category.short_ru, category.short_en = raw.get('shortRu'), raw.get('shortEn')
        category.card_type, category.facets = raw['cardType'], raw.get('facets') or []
        category.content = {key: value for key, value in (raw.get('content') or {}).items() if value}
        db.add(category)
        db.flush()
        found[category.path] = category
    set_setting(db, 'catalog_root', {key: value for key, value in root.items() if value})
    return found


def _substances(db: Session, rows: list[dict[str, Any]]) -> dict[str, Substance]:
    found = {substance.slug: substance for substance in db.scalars(select(Substance))}
    for raw in rows:
        substance = found.get(raw['slug']) or Substance(slug=raw['slug'])
        substance.name_ru, substance.name_en = raw['nameRu'], raw['nameEn']
        substance.cas, substance.formula = cas_or_none(raw.get('cas')), raw.get('formula')
        substance.molecular_weight, substance.synonyms = raw.get('molecularWeight'), raw.get('synonyms') or []
        substance.content = {key: value for key, value in (raw.get('content') or {}).items() if value}
        db.add(substance)
        found[substance.slug] = substance
    db.flush()
    return found


def _product(db: Session, raw: dict[str, Any], brands: dict[str, Brand], categories: dict[str, Category],
             substances: dict[str, Substance], register: controlled.Register) -> Product:
    brand = brands[raw['brand']]
    norm = compact(raw['catalogNumber'])
    product = db.scalar(select(Product).where(Product.brand_id == brand.id, Product.catalog_number_norm == norm))
    if product is None:
        product = Product(brand_id=brand.id, catalog_number_norm=norm, source='seed')
        db.add(product)
    substance = substances.get((raw.get('substance') or {}).get('slug', ''))
    cas = cas_or_none(raw.get('cas'))
    product.card_type, product.catalog_number, product.slug = raw['cardType'], raw['catalogNumber'], raw['slug']
    product.name_en, product.name_ru, product.synonyms = raw['name'], raw.get('nameRu'), raw.get('synonyms') or []
    product.cas = cas
    product.alt_cas = [c for c in (cas_or_none(value) for value in raw.get('altCas') or []) if c]
    product.substance_id = substance.id if substance else None
    product.substance_role = (raw.get('substance') or {}).get('role') if substance else None
    product.attributes = raw.get('attributes') or {}
    product.formula, product.formula_hill = raw.get('formula'), hill_key(raw.get('formula'))
    product.molecular_weight, product.iupac_name = raw.get('molecularWeight'), raw.get('iupacName')
    product.purity, product.storage, product.shipping = raw.get('purity'), raw.get('storage'), raw.get('shipping')
    product.dangerous_goods = raw.get('dangerousGoods')
    texts = raw.get('texts') or {}
    product.texts = {lang: {k: v for k, v in body.items() if v} for lang, body in texts.items() if body}
    product.unique_description = bool((texts.get('ru') or {}).get('description'))
    product.images = [raw['image']] if raw.get('image') else []
    product.custom_packaging = True if raw.get('customPackaging') and not brand.custom_packaging else None
    product.discontinued, product.popularity = bool(raw.get('discontinued')), int(raw.get('popularity') or 0)
    product.status = 'published'
    product.controlled, product.controlled_state = controlled.apply(
        register, name=product.name_en, cas=cas, synonyms=product.synonyms, current=product.controlled,
        state=product.controlled_state)
    db.flush()

    db.execute(delete(Packaging).where(Packaging.product_id == product.id))
    for i, pack in enumerate(raw.get('packagings') or []):
        parsed = parse_pack(pack['label'])
        db.add(Packaging(product_id=product.id, position=i, key=pack['key'], label_ru=pack['label'],
                         label_en=parsed.label_en if parsed else pack['label'],
                         amount=parsed.amount if parsed else None, unit=parsed.unit if parsed else None,
                         catalog_number=pack.get('catalogNumber'),
                         catalog_number_norm=compact(pack.get('catalogNumber')) or None))
    db.execute(delete(Document).where(Document.product_id == product.id))
    for i, doc in enumerate(raw.get('documents') or []):
        db.add(Document(product_id=product.id, position=i, type=doc['type'], lang=doc.get('lang') or 'en',
                        title_ru=doc.get('title'), title_en=doc.get('titleEn'), href=doc.get('href')))
    db.execute(delete(ProductCategory).where(ProductCategory.product_id == product.id))
    category = categories.get(raw.get('category') or '')
    if category:
        db.add(ProductCategory(product_id=product.id, category_id=category.id, is_primary=True))
    db.flush()
    return product


def load(db: Session, path: Path = SEED_FILE, *, products_too: bool = True) -> dict[str, int]:
    """The catalog structure and texts (categories, brand pages, substances, the root); with ``products_too`` —
    also the 413 test products, the register sample and the home selection (development and staging only)."""
    data = json.loads(path.read_text())
    brands = _brands(db, data['brands'])
    categories = _categories(db, data['categories'], data.get('root') or {})
    substances = _substances(db, data['substances'])
    pages, landings = load_content(db)
    if not products_too:
        return {'brands': len(brands), 'categories': len(categories), 'substances': len(substances),
                'pages': pages, 'landings': landings}
    controlled.load_register(db, data.get('controlled') or [])
    register = controlled.Register.load(db)
    weights, threshold = get_setting(db, 'completeness_weights'), get_setting(db, 'index_threshold')
    products = []
    for raw in data['products']:
        product = _product(db, raw, brands, categories, substances, register)
        refresh_card(db, product, weights=weights, threshold=threshold)
        products.append(product)
    set_setting(db, 'home_products', data.get('homeProducts') or [])
    db.flush()
    return {'brands': len(brands), 'categories': len(categories), 'substances': len(substances),
            'pages': pages, 'landings': landings, 'products': len(products),
            'controlled': sum(1 for p in products if p.controlled)}


def load_content(db: Session, path: Path = CONTENT_FILE) -> tuple[int, int]:
    """Pages and SEO landings of the site (ADM-02, ADM-07) that are not in the database yet: what was edited in
    the admin panel stays as it is."""
    from app.admin.models import ContentPage, SeoLanding

    if not path.exists():
        return 0, 0
    data = json.loads(path.read_text())
    pages = landings = 0
    existing = {(k, s) for k, s in db.execute(select(ContentPage.kind, ContentPage.slug))}
    for raw in data.get('pages') or []:
        if (raw['kind'], raw['slug']) not in existing:
            db.add(ContentPage(kind=raw['kind'], slug=raw['slug'], position=raw.get('position') or 0,
                               content=raw['content'], status='published', published_at=utcnow()))
            pages += 1
    known = {(p, s) for p, s in db.execute(select(SeoLanding.category_path, SeoLanding.slug))}
    for raw in data.get('landings') or []:
        if (raw['categoryPath'], raw['slug']) not in known:
            db.add(SeoLanding(category_path=raw['categoryPath'], slug=raw['slug'], filters=raw['filters'],
                              content=raw['content'], position=raw.get('position') or 0, status='published'))
            landings += 1
    db.flush()
    return pages, landings
