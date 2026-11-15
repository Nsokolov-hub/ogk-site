"""The indexing pilot of 03.11.2026: cards of chosen brands go to the index although their completeness is below the
threshold (SEO-07), because buyers search by catalog number and the imported cards score 30.

Only cards with a real name (not the importer's «<brand> <number>» stand-in), packagings and a CAS number or the
filter values of an HPLC column. The decision is the manual override of the admin panel (index_override = True),
marked seo.pilot with the date, so `undo` gives exactly these cards back to completeness.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import indexnow
from app.catalog.cas_pages import stand_in
from app.catalog.identity import indexed_as_alias, verified_identity
from app.catalog.models import Brand, Packaging, Product
from app.catalog.service import refresh_card
from app.catalog.settings import get_setting
from app.core.db import utcnow

COLUMN_KEYS = ('phase', 'length', 'diameter')


class UnknownBrands(Exception):
    pass


def _brands(db: Session, slugs: list[str]) -> dict[str, Brand]:
    found = {b.id: b for b in db.scalars(select(Brand).where(Brand.slug.in_(slugs)))}
    missing = set(slugs) - {b.slug for b in found.values()}
    if missing:
        raise UnknownBrands('Нет брендов: ' + ', '.join(sorted(missing)))
    return found


def eligible(product: Product, brand: Brand) -> bool:
    if stand_in(product.name_en, brand.name, product.catalog_number_norm):
        return False
    attributes: dict[str, Any] = product.attributes or {}
    return bool(product.cas or any(attributes.get(k) for k in COLUMN_KEYS) or verified_identity(product))


def open_cards(db: Session, slugs: list[str], limit: int | None,
               *, product_ids: list[str] | None = None) -> tuple[dict[str, int], int]:
    """The most popular eligible cards of the brands, up to limit in all; counts per brand and IndexNow entries."""
    brands = _brands(db, slugs)
    weights, threshold = get_setting(db, 'completeness_weights'), get_setting(db, 'index_threshold')
    statement = select(Product).where(Product.brand_id.in_(list(brands)), Product.status == 'published',
                              Product.controlled.is_(None), Product.discontinued.is_(False),
                              Product.indexable.is_(False), Product.index_override.is_(None),
                              Product.id.in_(select(Packaging.product_id)))
    if product_ids is not None:
        statement = statement.where(Product.id.in_(product_ids))
    candidates = db.scalars(statement.order_by(Product.popularity.desc(), Product.name_en))
    chosen: list[Product] = []
    for product in candidates:
        if eligible(product, brands[product.brand_id]) and not indexed_as_alias(db, product):
            chosen.append(product)
            if limit and len(chosen) >= limit:
                break
    today = utcnow().date().isoformat()
    counts: dict[str, int] = {}
    for product in chosen:
        product.index_override = True
        product.seo = {**(product.seo or {}), 'pilot': today}
        refresh_card(db, product, weights=weights, threshold=threshold)
        slug = brands[product.brand_id].slug
        counts[slug] = counts.get(slug, 0) + 1
    db.flush()
    return counts, indexnow.queue(db, [f'/product/{p.slug}/' for p in chosen if p.indexable])


def quality_report(db: Session, slugs: list[str], limit: int = 25) -> dict[str, Any]:
    """A bounded commercial pilot and its published-page coverage, without creating demo products or content.

    Existing indexed pages are monitored as well; only an explicit apply opens eligible, unindexed candidates.
    The report exposes completeness/source so the operator can review real cards rather than lower a global gate.
    """
    if not 20 <= limit <= 50:
        raise ValueError('Для пилота укажите от 20 до 50 карточек')
    brands = _brands(db, slugs)
    coverage = []
    for brand in brands.values():
        scope = (Product.brand_id == brand.id, Product.status == 'published', Product.controlled.is_(None),
                 Product.discontinued.is_(False), Product.source != 'seed')
        total = db.scalar(select(func.count()).select_from(Product).where(*scope)) or 0
        indexed = db.scalar(select(func.count()).select_from(Product).where(*scope, Product.indexable.is_(True))) or 0
        coverage.append({'brand': brand.slug, 'published': total, 'indexable': indexed})
    statement = select(Product).where(Product.brand_id.in_(list(brands)), Product.status == 'published',
                                      Product.controlled.is_(None), Product.discontinued.is_(False),
                                      Product.source != 'seed', Product.id.in_(select(Packaging.product_id)))
    rows = db.scalars(statement.order_by(Product.popularity.desc(), Product.completeness.desc(), Product.name_en))
    candidates = []
    for product in rows:
        if not eligible(product, brands[product.brand_id]) or indexed_as_alias(db, product):
            continue
        candidates.append({'id': product.id, 'slug': product.slug, 'brand': brands[product.brand_id].slug,
                           'catalogNumber': product.catalog_number, 'name': product.name_en,
                           'url': f'https://www.ogk-chem.ru/product/{product.slug}/',
                           'completeness': product.completeness, 'indexable': product.indexable,
                           'source': product.source, 'verifiedIdentity': bool(verified_identity(product)),
                           'uniqueDescription': product.unique_description,
                           'action': 'monitor' if product.indexable else
                           'explicit_noindex' if product.index_override is False else 'pilot_override'})
        if len(candidates) >= limit:
            break
    return {'limit': limit, 'coverage': coverage, 'candidates': candidates,
            'selected': len(candidates), 'shortfall': max(0, limit - len(candidates)),
            'note': 'Это опубликованные страницы сайта, не данные фактического индекса Яндекса или Google.'}


def apply_quality_pilot(db: Session, slugs: list[str], limit: int = 25) -> dict[str, Any]:
    report = quality_report(db, slugs, limit)
    ids = [row['id'] for row in report['candidates'] if row['action'] == 'pilot_override']
    counts, queued = open_cards(db, slugs, limit, product_ids=ids)
    return {**report, 'opened': counts, 'queued': queued, 'applied': True}


def undo(db: Session, slugs: list[str]) -> tuple[dict[str, int], int]:
    """The pilot's cards of the brands back to the completeness rule."""
    brands = _brands(db, slugs)
    weights, threshold = get_setting(db, 'completeness_weights'), get_setting(db, 'index_threshold')
    rows = [p for p in db.scalars(select(Product).where(Product.brand_id.in_(list(brands)),
                                                        Product.index_override.is_(True)))
            if (p.seo or {}).get('pilot')]
    counts: dict[str, int] = {}
    for product in rows:
        product.index_override = None
        product.seo = {k: v for k, v in (product.seo or {}).items() if k != 'pilot'}
        refresh_card(db, product, weights=weights, threshold=threshold)
        slug = brands[product.brand_id].slug
        counts[slug] = counts.get(slug, 0) + 1
    db.flush()
    return counts, indexnow.queue(db, [f'/product/{p.slug}/' for p in rows])
