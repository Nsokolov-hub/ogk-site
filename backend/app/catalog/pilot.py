"""The indexing pilot of 03.11.2026: cards of chosen brands go to the index although their completeness is below the
threshold (SEO-07), because buyers search by catalog number and the imported cards score 30.

Only cards with a real name (not the importer's «<brand> <number>» stand-in), packagings and a CAS number or the
filter values of an HPLC column. The decision is the manual override of the admin panel (index_override = True),
marked seo.pilot with the date, so `undo` gives exactly these cards back to completeness.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import indexnow
from app.catalog.cas_pages import stand_in
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
    return bool(product.cas or any(attributes.get(k) for k in COLUMN_KEYS))


def open_cards(db: Session, slugs: list[str], limit: int | None) -> tuple[dict[str, int], int]:
    """The most popular eligible cards of the brands, up to limit in all; counts per brand and IndexNow entries."""
    brands = _brands(db, slugs)
    weights, threshold = get_setting(db, 'completeness_weights'), get_setting(db, 'index_threshold')
    candidates = db.scalars(
        select(Product).where(Product.brand_id.in_(list(brands)), Product.status == 'published',
                              Product.controlled.is_(None), Product.discontinued.is_(False),
                              Product.indexable.is_(False), Product.index_override.is_(None),
                              Product.id.in_(select(Packaging.product_id)))
        .order_by(Product.popularity.desc(), Product.name_en))
    chosen: list[Product] = []
    for product in candidates:
        if eligible(product, brands[product.brand_id]):
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
