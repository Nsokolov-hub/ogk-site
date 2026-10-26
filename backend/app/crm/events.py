"""Events of the CRM, flow F2 (my-crm-project docs/site-integration.md).

The CRM POSTs every event to /api/v1/crm/events, signed with HMAC-SHA256 over ``<timestamp>.<body>`` by the key both
sides share (CRM_EVENTS_SECRET here, SITE_EVENTS_SECRET in the CRM). An event is applied once: a repeat with the same
id gets the first answer back. What the site does with them:

- ``site_request.*``, ``request.*`` — the fate of a site request and the stage of the CRM request made from it are
  shown in the admin journal; stages become offline conversions in Metrica and GA4 (flow F3, app.crm.conversions);
- ``product.upserted`` — a position marked «Публиковать на сайте» becomes a card waiting for moderation, or is linked
  to the card the site already has; the answer carries the card's id (flow F4). The site stays the master of its
  texts: the CRM only fills what is empty;
- ``manufacturer.*`` — the registry changed: the load of brands (flow F5) runs without waiting for the night.

Unknown types and requests the site does not know are accepted and ignored, so the CRM does not retry them.
"""

import hashlib
import hmac
import ipaddress
import time
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import Brand, BrandAlias, Packaging, Product
from app.catalog.normalize import brand_key, cas_or_none, clean_spaces, compact, parse_pack, slugify
from app.catalog.service import refresh_card, unique_product_slug
from app.catalog.settings import set_setting
from app.core.config import settings
from app.core.db import DB, utcnow
from app.core.errors import DomainError
from app.crm import conversions
from app.crm.models import CrmEvent
from app.requests.models import SiteRequest

router = APIRouter(include_in_schema=False)
MAX_SKEW_SECONDS = 300
# Stages of a CRM request in their order, and the first stage that reaches each goal of the offline conversions
# (the CRM's report by channels counts «qualified» the same way).
STAGES = ('new', 'clarification', 'collecting_quotes', 'quote_given', 'calculation', 'proposal_sent',
          'composition_agreed', 'awaiting_payment', 'sale_confirmed')
GOALS = (('qualified', 'collecting_quotes'), ('proposal', 'proposal_sent'), ('sale', 'sale_confirmed'))


class EventIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=60)
    occurred_at: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


def address_allowed(host: str | None) -> bool:
    networks = [part.strip() for part in settings.crm_events_allowed_ips.split(',') if part.strip()]
    if not networks:
        return True
    try:
        address = ipaddress.ip_address(host or '')
    except ValueError:
        return False
    for network in networks:
        try:
            if address in ipaddress.ip_network(network, strict=False):
                return True
        except ValueError:
            continue
    return False


def verify(headers: dict[str, str], body: bytes, now: float | None = None) -> None:
    stamp = headers.get('x-crm-timestamp', '')
    if not stamp.isdigit():
        raise DomainError('CRM_SIGNATURE_INVALID', 'Нет отметки времени', 401)
    if abs((now if now is not None else time.time()) - int(stamp)) > MAX_SKEW_SECONDS:
        raise DomainError('CRM_SIGNATURE_EXPIRED', 'Подпись устарела: сверьте часы серверов', 401)
    expected = 'sha256=' + hmac.new(settings.crm_events_secret.encode(), stamp.encode() + b'.' + body,
                                    hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, headers.get('x-crm-signature', '')):
        raise DomainError('CRM_SIGNATURE_INVALID', 'Подпись неверна', 401)


# ── site requests and the stages of their CRM requests ──

def site_request_of(db: Session, data: dict[str, Any]) -> SiteRequest | None:
    request_id = data.get('site_request_id')
    return db.get(SiteRequest, request_id) if isinstance(request_id, str) and request_id else None


def touched(row: SiteRequest) -> None:
    row.crm_updated_at = utcnow()
    row.version += 1


def on_site_request(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    row = site_request_of(db, data)
    if row is None:
        return {'ignored': 'SITE_REQUEST_UNKNOWN'}
    row.crm_status = clean_spaces(str(data.get('status') or ''))[:20] or row.crm_status
    touched(row)
    return {}


def on_stage(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    row = site_request_of(db, data)
    if row is None:
        return {'ignored': 'SITE_REQUEST_UNKNOWN'}
    stage = clean_spaces(str(data.get('stage') or ''))[:40]
    row.crm_stage = stage or row.crm_stage
    if data.get('crm_request_number'):
        row.crm_request_number = str(data['crm_request_number'])[:40]
    revenue = data.get('revenue')
    if stage == 'sale_confirmed' and isinstance(revenue, dict):
        try:
            row.sale_amount = Decimal(str(revenue.get('amount'))).quantize(Decimal('0.01'))
        except InvalidOperation:
            row.sale_amount = None
        row.sale_currency = str(revenue.get('currency') or 'RUB').upper()[:3]
    touched(row)
    queued = 0
    if stage in STAGES:
        for goal, first in GOALS:
            if STAGES.index(stage) >= STAGES.index(first):
                queued += conversions.queue(db, row, goal)
    return {'conversions': queued}


def on_closed(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    row = site_request_of(db, data)
    if row is None:
        return {'ignored': 'SITE_REQUEST_UNKNOWN'}
    row.crm_stage = 'lost' if data.get('lost') else (clean_spaces(str(data.get('stage') or ''))[:40] or row.crm_stage)
    touched(row)
    return {}


# ── products marked «Публиковать на сайте» (flow F4) ──

def brand_for(db: Session, data: dict[str, Any]) -> Brand | None:
    """The brand by the CRM's manufacturer id, else by a known spelling; a new one is created without a page."""
    crm_id = str(data.get('crm_manufacturer_id') or '')[:36]
    name = clean_spaces(str(data.get('brand') or ''))[:200]
    brand = db.scalar(select(Brand).where(Brand.crm_manufacturer_id == crm_id)) if crm_id else None
    if brand is None and brand_key(name):
        alias = db.scalar(select(BrandAlias).where(BrandAlias.normalized == brand_key(name)))
        brand = db.get(Brand, alias.brand_id) if alias else None
    seen: set[str] = set()
    while brand is not None and brand.merged_into_id and brand.id not in seen:
        seen.add(brand.id)
        brand = db.get(Brand, brand.merged_into_id)
    if brand is None and brand_key(name):
        slug, n = slugify(name, 100) or f'brand-{brand_key(name)[:20]}', 1
        while db.scalar(select(Brand.id).where(Brand.slug == slug)):
            n += 1
            slug = f'{slugify(name, 95)}-{n}'
        brand = Brand(slug=slug, name=name, page_published=False, content={}, crm_manufacturer_id=crm_id or None)
        db.add(brand)
        db.flush()
        db.add(BrandAlias(brand_id=brand.id, name=name[:250], normalized=brand_key(name), source='crm'))
    return brand


def add_packagings(db: Session, product: Product, labels: object) -> int:
    if not isinstance(labels, list):
        return 0
    rows = list(db.scalars(select(Packaging).where(Packaging.product_id == product.id)))
    keys = {row.key for row in rows}
    position = max((row.position for row in rows), default=-1)
    added = 0
    for label in labels:
        pack = parse_pack(str(label)) if isinstance(label, str | int | float) else None
        if pack is None or pack.key in keys:
            continue
        keys.add(pack.key)
        position += 1
        db.add(Packaging(product_id=product.id, position=position, key=pack.key, amount=pack.amount, unit=pack.unit,
                         label_ru=pack.label_ru[:120], label_en=pack.label_en[:120], availability='on_order'))
        added += 1
    db.flush()
    return added


def on_product(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    crm_id = str(data.get('crm_product_id') or '')[:36]
    if not crm_id:
        raise DomainError('CRM_EVENT_INVALID', 'Нет crm_product_id', 422)
    publish = bool(data.get('publish'))
    number = clean_spaces(str(data.get('catalog_number') or ''))[:150]
    site_id = data.get('site_product_id')
    product = db.get(Product, site_id) if isinstance(site_id, str) and site_id else None
    if product is None:
        product = db.scalar(select(Product).where(Product.crm_product_id == crm_id).limit(1))
    if product is None:
        if not publish:
            return {'ignored': 'NOT_PUBLISHED'}
        if not compact(number):
            return {'ignored': 'NO_CATALOG_NUMBER'}
        brand = brand_for(db, data)
        if brand is None:
            return {'ignored': 'NO_BRAND'}
        product = db.scalar(select(Product).where(Product.brand_id == brand.id,
                                                  Product.catalog_number_norm == compact(number)))
        if product is None:
            name = clean_spaces(str(data.get('name') or ''))[:500] or number
            product = Product(brand_id=brand.id, catalog_number=number, catalog_number_norm=compact(number),
                              slug=unique_product_slug(db, brand.slug, number, name), name_en=name,
                              cas=cas_or_none(str(data.get('cas') or '')),
                              purity=clean_spaces(str(data.get('purity') or ''))[:200] or None,
                              source='crm', status='moderation', crm_product_id=crm_id)
            db.add(product)
            db.flush()
            add_packagings(db, product, data.get('packagings'))
            refresh_card(db, product)
            return {'site_product_id': product.id, 'created': True}
    # A card the site already has: linked, and only empty fields are filled; the texts stay the site's.
    if product.crm_product_id is None:
        product.crm_product_id = crm_id
    manual = set(product.manual_fields or [])
    if product.cas is None and 'cas' not in manual:
        product.cas = cas_or_none(str(data.get('cas') or ''))
    if not product.purity and 'purity' not in manual:
        product.purity = clean_spaces(str(data.get('purity') or ''))[:200] or None
    add_packagings(db, product, data.get('packagings'))
    if product.source == 'crm' and product.status in ('draft', 'moderation'):
        # Unticked in the CRM before moderation: the card leaves the queue (ticked again — it comes back).
        product.status = 'moderation' if publish else 'draft'
    product.version += 1
    refresh_card(db, product)
    return {'site_product_id': product.id}


def on_manufacturer(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    # The registry is loaded whole (merges, aliases, new names): the next worker iteration runs it.
    set_setting(db, 'brands_sync_run_at', None)
    return {}


HANDLERS: dict[str, Callable[[Session, dict[str, Any]], dict[str, Any]]] = {
    'site_request.assigned': on_site_request, 'site_request.converted': on_site_request,
    'site_request.rejected': on_site_request, 'request.stage_changed': on_stage, 'request.closed': on_closed,
    'product.upserted': on_product, 'manufacturer.upserted': on_manufacturer,
    'manufacturer.merged': on_manufacturer,
}


def apply(db: Session, event: EventIn) -> dict[str, Any]:
    known = db.get(CrmEvent, event.id)
    if known is not None:
        return known.answer
    handler = HANDLERS.get(event.type)
    answer = {'ok': True, **(handler(db, event.data) if handler else {'ignored': 'UNKNOWN_TYPE'})}
    db.add(CrmEvent(id=event.id, type=event.type, answer=answer))
    db.flush()
    return answer


@router.post('/crm/events')
async def receive(request: Request, db: DB) -> dict[str, Any]:
    if not settings.crm_events_secret:
        raise DomainError('CRM_EVENTS_DISABLED', 'Приём событий CRM не настроен (CRM_EVENTS_SECRET)', 503)
    if not address_allowed(request.client.host if request.client else None):
        raise DomainError('CRM_ADDRESS_FORBIDDEN', 'Адрес не разрешён', 403)
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    verify(headers, body)
    try:
        event = EventIn.model_validate_json(body)
    except ValidationError:
        raise DomainError('CRM_EVENT_INVALID', 'Событие не прошло проверку', 422) from None
    if headers.get('x-crm-event-id', event.id) != event.id:
        raise DomainError('CRM_EVENT_INVALID', 'Идентификатор события не совпадает', 422)
    return await run_in_threadpool(apply, db, event)
