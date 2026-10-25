"""Manufacturer registry from the CRM (flow F5, TZ 9.3): brands and their spellings follow the CRM.

The worker loads the changes every night (``python -m app.catalog.cli sync-brands`` does it at once):

- a CRM manufacturer is linked to the site brand with the same spelling, or becomes a brand without a page;
- every CRM spelling becomes an alias, so imports recognise the manufacturer in price lists (IMP-03);
- a manufacturer merged in the CRM moves its products to the main brand, its page answers 301 to the main one.

Brand pages, logos and texts stay on the site: the CRM is the master of the registry only.
"""

import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import Brand, BrandAlias, Product
from app.catalog.normalize import brand_key, slugify
from app.catalog.service import change_slug
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.core.db import as_utc, utcnow
from app.core.logs import event

logger = logging.getLogger('site.brands')
PATH = '/api/v1/integrations/site/manufacturers'


class SyncFailed(Exception):
    pass


def configured() -> bool:
    return bool(settings.crm_url and settings.crm_token and settings.crm_signing_secret)


def signed_get(client: httpx.Client, params: dict[str, Any]) -> dict[str, Any]:
    """The same signature as F1, over «GET <path>?<query>» instead of a body."""
    query = urlencode({k: v for k, v in params.items() if v is not None})
    target = PATH + (f'?{query}' if query else '')
    stamp = str(int(time.time()))
    digest = hmac.new(settings.crm_signing_secret.encode(), f'{stamp}.GET {target}'.encode(), hashlib.sha256)
    try:
        response = client.get(target, headers={'Authorization': f'Bearer {settings.crm_token}',
                                               'X-Site-Timestamp': stamp,
                                               'X-Site-Signature': f'sha256={digest.hexdigest()}'})
    except httpx.HTTPError as exc:
        raise SyncFailed(f'CRM недоступна: {exc}') from exc
    if response.status_code != 200:
        raise SyncFailed(f'CRM ответила {response.status_code}: {response.text[:200]}')
    data: dict[str, Any] = response.json()
    return data


def _unique_slug(db: Session, name: str) -> str:
    base = slugify(name, 100) or 'brand'
    slug, n = base, 1
    while db.scalar(select(Brand.id).where(Brand.slug == slug)):
        n += 1
        slug = f'{base[:95]}-{n}'
    return slug


def apply_entry(db: Session, item: dict[str, Any], counters: dict[str, int]) -> Brand:
    brand = db.scalar(select(Brand).where(Brand.crm_manufacturer_id == item['id']))
    spellings = [item['name'], *item.get('aliases', [])]
    if brand is None:
        for spelling in spellings:
            alias = db.scalar(select(BrandAlias).where(BrandAlias.normalized == brand_key(spelling)))
            candidate = db.get(Brand, alias.brand_id) if alias else \
                db.scalar(select(Brand).where(Brand.slug == slugify(spelling, 100)))
            if candidate is not None and candidate.crm_manufacturer_id is None:
                brand = candidate
                counters['linked'] += 1
                break
    if brand is None:
        brand = Brand(slug=_unique_slug(db, item['name']), name=item['name'][:200], page_published=False,
                      content={})
        db.add(brand)
        counters['created'] += 1
    brand.crm_manufacturer_id = item['id']
    db.flush()
    for spelling in spellings:
        key = brand_key(spelling)
        if not key:
            continue
        alias = db.scalar(select(BrandAlias).where(BrandAlias.normalized == key))
        if alias is None:
            db.add(BrandAlias(brand_id=brand.id, name=spelling[:250], normalized=key, source='crm'))
            counters['aliases'] += 1
        elif alias.brand_id != brand.id:
            # The spelling belongs to another site brand: a person decides (merge in the CRM or rename).
            counters['alias_conflicts'] += 1
    db.flush()
    return brand


def merge(db: Session, source: Brand, target: Brand) -> int:
    """Products of a merged brand go to the main one; a number the main brand already has stays put."""
    if source.id == target.id or source.merged_into_id == target.id:
        return 0
    taken = set(db.scalars(select(Product.catalog_number_norm).where(Product.brand_id == target.id)))
    movable = [pid for pid, norm in db.execute(select(Product.id, Product.catalog_number_norm)
                                               .where(Product.brand_id == source.id)) if norm not in taken]
    for start in range(0, len(movable), 5000):
        db.execute(update(Product).where(Product.id.in_(movable[start:start + 5000]))
                   .values(brand_id=target.id, needs_index=True, updated_at=utcnow()))
    db.execute(update(BrandAlias).where(BrandAlias.brand_id == source.id).values(brand_id=target.id))
    source.merged_into_id = target.id
    if source.page_published:
        change_slug(db, 'brand', target.id, source.slug, target.slug)
    db.flush()
    return len(movable)


def sync(session_factory: sessionmaker[Session], *, transport: httpx.BaseTransport | None = None) -> dict[str, Any]:
    if not configured():
        return {'skipped': 'CRM_URL, CRM_TOKEN и CRM_SIGNING_SECRET не заданы'}
    counters: dict[str, int] = {'entries': 0, 'created': 0, 'linked': 0, 'aliases': 0, 'alias_conflicts': 0,
                                'merged': 0, 'moved_products': 0}
    with session_factory() as db:
        since = get_setting(db, 'brands_synced_at')
    newest: datetime | None = None
    merges: list[tuple[str, str]] = []
    cursor = None
    with httpx.Client(base_url=settings.crm_url.rstrip('/'), timeout=settings.crm_timeout_seconds,
                      transport=transport) as client:
        while True:
            page = signed_get(client, {'updated_since': since, 'cursor': cursor, 'limit': 500})
            with session_factory.begin() as db:
                for item in page['items']:
                    apply_entry(db, item, counters)
                    counters['entries'] += 1
                    stamp = as_utc(datetime.fromisoformat(item['updated_at']))
                    newest = stamp if newest is None or stamp > newest else newest
                    if item.get('merged_into_id'):
                        merges.append((item['id'], item['merged_into_id']))
            cursor = page.get('next_cursor')
            if not cursor:
                break
    with session_factory.begin() as db:
        for source_id, target_id in merges:
            source = db.scalar(select(Brand).where(Brand.crm_manufacturer_id == source_id))
            target = db.scalar(select(Brand).where(Brand.crm_manufacturer_id == target_id))
            if source and target:
                moved = merge(db, source, target)
                counters['merged'] += 1
                counters['moved_products'] += moved
        if newest is not None:
            set_setting(db, 'brands_synced_at', newest.isoformat())
        set_setting(db, 'brands_sync_run_at', utcnow().isoformat())
    event(logger, 'brands_synced', **counters)
    return counters


def due(db: Session, now: datetime | None = None) -> bool:
    """Once a day (TZ 9.3: the nightly load)."""
    last = get_setting(db, 'brands_sync_run_at')
    if not last:
        return True
    return (now or utcnow()) - as_utc(datetime.fromisoformat(last)) >= timedelta(hours=24)
