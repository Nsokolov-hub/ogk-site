"""Catalog settings kept in the database (ADM-10 will edit them); defaults until someone changes them."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import CatalogSetting

DEFAULTS: dict[str, Any] = {
    # TZ 5.6: weights of completeness and the threshold of indexing; the starting threshold is 70.
    'completeness_weights': {'identity': 20, 'image': 15, 'description': 25, 'document': 15, 'link': 10,
                             'storage': 15},
    'index_threshold': 70,
    # TZ 5.2.1: products of the lists are hidden from the storefront, search, Sitemap and the feed.
    'hide_controlled': True,
    # TZ 15.4: categories (path prefixes) and brands of the Yandex Direct feed; empty brands — all.
    'feed': {'categories': ['reference-standards', 'chromatography', 'reagents', 'biological-standards',
                            'laboratory-equipment'], 'brands': []},
    # Texts of the catalog root /catalog/: {"ru": CategoryContent, "en": CategoryContent}.
    'catalog_root': {},
    # Products of the home page block, by slug, in order.
    'home_products': [],
    # Flow F5: the newest change of the CRM registry already loaded, and when the last load ran.
    'brands_synced_at': None,
    'brands_sync_run_at': None,
}


def get_setting(db: Session, key: str) -> Any:
    row = db.scalar(select(CatalogSetting).where(CatalogSetting.key == key))
    return DEFAULTS[key] if row is None else row.value


def set_setting(db: Session, key: str, value: Any) -> None:
    if key not in DEFAULTS:
        raise KeyError(key)
    row = db.get(CatalogSetting, key)
    if row is None:
        db.add(CatalogSetting(key=key, value=value))
    else:
        row.value = value
    db.flush()
