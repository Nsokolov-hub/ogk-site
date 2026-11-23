"""Private stock catalogue for the CRM. Uses the existing signed CRM channel, never a public route."""

import base64
import binascii
import json
from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import and_, exists, false, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.catalog.identity import CHANNEL_SLUG, MASTER_SLUG, indexed_as_alias, verified_identity
from app.catalog.models import Brand, CompetitorOffer, Packaging, Product
from app.catalog.settings import get_setting
from app.catalog.stock_availability import iso, offer_view, public_products
from app.core.config import settings
from app.core.db import DB, as_utc, utcnow
from app.core.errors import DomainError
from app.crm.events import address_allowed, verify

router = APIRouter(include_in_schema=False)


class StockIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['catalog', 'review'] = 'catalog'
    q: str = Field(default='', max_length=200)
    source: str = Field(default='', max_length=30)
    brand: str = Field(default='', max_length=200)
    cursor: str | None = Field(default=None, max_length=4096)
    limit: int = Field(default=100, ge=1, le=200)
    as_of: datetime | None = None


def cursor_token(key: list[str], body: StockIn, at: datetime) -> str:
    payload = [body.mode, body.q, body.source, body.brand, iso(at), key]
    return base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode().rstrip('=')


def read_cursor(body: StockIn, at: datetime) -> list[str] | None:
    if not body.cursor:
        return None
    try:
        values = json.loads(base64.urlsafe_b64decode(body.cursor + '=' * (-len(body.cursor) % 4)))
        if values[:5] != [body.mode, body.q, body.source, body.brand, iso(at)]:
            raise ValueError('different filters')
        key = values[5]
        expected = 2 if body.mode == 'catalog' else 1
        if len(values) != 6 or not isinstance(key, list) or len(key) != expected or any(
                not isinstance(part, str) or len(part) > 36 for part in key):
            raise ValueError('key')
        return key
    except (ValueError, TypeError, IndexError, binascii.Error):
        raise DomainError('STOCK_CURSOR_INVALID', 'Страница каталога устарела. Обновите список', 422, 'cursor') from None


def source_status(db: Session) -> list[dict[str, Any]]:
    from app.catalog.competitors import META, NAMES, fresh_offers

    results = get_setting(db, 'competitor_results') or {}
    checks = results.get('sources') or results.get('stats') or {}
    run = get_setting(db, 'competitor_run') or {}
    current = run.get('stats') or {}
    refresh_result = get_setting(db, 'competitor_refresh_results') or {}
    refresh_checks = refresh_result.get('sources') or {}
    refresh_run = get_setting(db, 'competitor_refresh_run') or {}
    refresh_current = refresh_run.get('stats') or {}
    config = get_setting(db, 'competitor_stock') or {}
    # A page may repeat a warehouse row. Persisted observations and exact, fresh packaging matches explain
    # the difference between rows parsed, rows awaiting review and goods usable by our catalogue.
    stored = dict(db.execute(select(CompetitorOffer.source, func.count()).group_by(CompetitorOffer.source)).all())
    review_counts = dict(db.execute(select(CompetitorOffer.source, func.count()).where(or_(
        CompetitorOffer.product_id.is_(None), CompetitorOffer.packaging_id.is_(None)))
        .group_by(CompetitorOffer.source)).all())
    fresh = fresh_offers(db)
    fresh_counts = dict(db.execute(fresh.with_only_columns(CompetitorOffer.source, func.count())
                                  .group_by(CompetitorOffer.source)).all())
    exact_counts = dict(db.execute(fresh.join(Packaging, and_(
        Packaging.id == CompetitorOffer.packaging_id, Packaging.product_id == CompetitorOffer.product_id))
        .with_only_columns(CompetitorOffer.source, func.count(func.distinct(CompetitorOffer.packaging_id)))
        .group_by(CompetitorOffer.source)).all())
    pending: dict[str, int] = {}
    for task in run.get('queue') or []:
        pending[task['s']] = pending.get(task['s'], 0) + 1
    refresh_pending: dict[str, int] = {}
    for task in refresh_run.get('queue') or []:
        refresh_pending[task['s']] = refresh_pending.get(task['s'], 0) + 1
    sources = []
    for code, name in sorted(NAMES.items(), key=lambda entry: entry[1]):
        check = {'checked_at': results.get('finishedAt'), **checks[code]} if code in checks else None
        if code in current:
            # Do not present a previous completed check as the outcome of the active crawl. Its counters
            # are available immediately, including sources that found only offers for manager review.
            check = {'checked_at': None, **current[code], 'complete': False, 'running': True,
                     'started_at': run.get('startedAt'), 'pending_pages': pending.get(code, 0)}
        refresh = ({'checked_at': refresh_result.get('finishedAt'), 'running': False,
                    'started_at': refresh_result.get('startedAt'), **refresh_checks[code]}
                   if code in refresh_checks else None)
        if code in refresh_current:
            refresh = {'checked_at': None, **refresh_current[code], 'complete': False, 'running': True,
                       'started_at': refresh_run.get('startedAt'), 'pending_pages': refresh_pending.get(code, 0)}
        if refresh is not None:
            # A known-stock refresh is narrower than catalogue discovery. Keep its history/progress separate
            # rather than replacing a completed warehouse crawl with a misleading partial result.
            check = {**(check or {}), 'refresh': {**refresh, 'scope': 'known_stock',
                     'interval_hours': config.get('refresh_hours') or 2,
                     'fresh_hours': config.get('fresh_hours') or 6}}
        if check is not None or code in stored:
            check = {**(check or {}), 'stored_offers': int(stored.get(code, 0)),
                     'fresh_offers': int(fresh_counts.get(code, 0)),
                     'exact_packagings': int(exact_counts.get(code, 0)),
                     'pending_review': int(review_counts.get(code, 0))}
        sources.append({'id': code, 'name': name, 'status': META.get(code, {}).get('status', 'configured'),
                        'reason': META.get(code, {}).get('reason', ''), 'last_check': check})
    return sources


def catalog(db: Session, body: StockIn, at: datetime, key: list[str] | None) -> tuple[list[dict[str, Any]], bool, list[str] | None]:
    from app.catalog.competitors import fresh_offers

    fresh = fresh_offers(db, max(as_utc(at), as_utc(utcnow())))
    if body.source:
        fresh = fresh.where(CompetitorOffer.source == body.source)
    supplier_keys = fresh.with_only_columns(
        CompetitorOffer.product_id.label('product_id'), CompetitorOffer.packaging_id.label('packaging_id')
    ).join(Packaging, and_(Packaging.id == CompetitorOffer.packaging_id,
                          Packaging.product_id == CompetitorOffer.product_id))
    other = aliased(Packaging)
    single_pack = ~exists(select(other.id).where(other.product_id == Product.id, other.id != Packaging.id))
    # The explicit identity review retains historic placeholders. Query its two indexed slugs, never scan
    # the full product catalogue for JSON, and count only the reviewed public packaging for own stock.
    reviewed = list(db.scalars(select(Product).where(Product.slug.in_([MASTER_SLUG, CHANNEL_SLUG]))))
    aliases = [product.id for product in reviewed if indexed_as_alias(db, product)]
    approved = {product.id: identity['verifiedPackagingId'] for product in reviewed
                if (identity := verified_identity(product)) and isinstance(identity.get('verifiedPackagingId'), str)}
    if body.source:
        eligible = supplier_keys.distinct().subquery('eligible_stock')
    else:
        pack_stock = select(Packaging.product_id.label('product_id'), Packaging.id.label('packaging_id')).where(
            Packaging.availability == 'in_stock')
        approved_pairs = [and_(Product.id == product_id, Packaging.id == pack_id)
                          for product_id, pack_id in approved.items()]
        approved_pack = or_(*approved_pairs) if approved_pairs else false()
        product_stock = select(Product.id.label('product_id'), Packaging.id.label('packaging_id')).join(
            Packaging, Packaging.product_id == Product.id).where(
                Product.availability == 'in_stock', or_(single_pack, approved_pack))
        # Deduplicate stock evidence before pagination. Starting from these narrow keys avoids a
        # correlated supplier EXISTS for every product/packaging in the full catalogue.
        eligible = supplier_keys.union(pack_stock, product_stock).subquery('eligible_stock')
    query = select(Product, Packaging, Brand).select_from(eligible).join(
        Product, Product.id == eligible.c.product_id).join(
        Packaging, and_(Packaging.id == eligible.c.packaging_id, Packaging.product_id == Product.id)).join(
        Brand, Brand.id == Product.brand_id).where(public_products(db))
    if aliases:
        query = query.where(Product.id.not_in(aliases))
    for product_id, pack_id in approved.items():
        query = query.where(or_(Product.id != product_id, Packaging.id == pack_id))
    if body.q.strip():
        query = query.where(or_(*(col.contains(body.q.strip(), autoescape=True) for col in
                            (Product.name_ru, Product.name_en, Product.catalog_number, Product.cas,
                             Packaging.catalog_number, Brand.name))))
    if body.brand.strip():
        query = query.where(or_(Brand.name.contains(body.brand.strip(), autoescape=True), Brand.slug == body.brand.strip()))
    if key:
        query = query.where(or_(Product.id > key[0], and_(Product.id == key[0], Packaging.id > key[1])))
    found = list(db.execute(query.order_by(Product.id, Packaging.id).limit(body.limit + 1)))
    selected = found[:body.limit]
    pack_ids = [pack.id for _, pack, _ in selected]
    offers = list(db.scalars(fresh.join(Packaging, Packaging.id == CompetitorOffer.packaging_id).where(
                            CompetitorOffer.packaging_id.in_(pack_ids),
                            CompetitorOffer.product_id == Packaging.product_id)
                            .order_by(CompetitorOffer.source, CompetitorOffer.id))) if pack_ids else []
    by_pack: dict[str, list[CompetitorOffer]] = {}
    for offer in offers:
        by_pack.setdefault(offer.packaging_id or '', []).append(offer)
    rows = []
    for product, pack, brand in selected:
        evidence = by_pack.get(pack.id, [])
        has_own = pack.availability == 'in_stock' or product.availability == 'in_stock' and (product.id in approved or
            db.scalar(select(func.count()).select_from(Packaging).where(Packaging.product_id == product.id)) == 1)
        identity = verified_identity(product)
        rows.append({'id': f'{product.id}:{pack.id}', 'product_id': product.id, 'packaging_id': pack.id,
                     'name': product.name_ru or product.name_en, 'article': pack.catalog_number or product.catalog_number,
                     'cas': product.cas, 'manufacturer': identity['manufacturer'] if identity else brand.name,
                     'purity': product.purity,
                     'packaging': pack.label_ru or pack.label_en, 'availability': 'in_stock',
                     'checked_at': iso(max((offer.seen_at for offer in evidence), key=as_utc)) if evidence else iso(at),
                     'product_url': settings.site_url.rstrip('/') + '/product/' + product.slug + '/',
                     'origin': 'own' if has_own else 'supplier',
                     'offers': [offer_view(db, offer) for offer in evidence]})
    last = [selected[-1][0].id, selected[-1][1].id] if selected else None
    return rows, len(found) > body.limit, last


def review(db: Session, body: StockIn, at: datetime, key: list[str] | None) -> tuple[list[dict[str, Any]], bool, list[str] | None]:
    from app.catalog.competitors import offer_valid_until

    query = select(CompetitorOffer).where(or_(CompetitorOffer.product_id.is_(None),
                                               CompetitorOffer.packaging_id.is_(None)))
    if body.q.strip():
        query = query.where(or_(*(col.contains(body.q.strip(), autoescape=True) for col in
                    (CompetitorOffer.name, CompetitorOffer.catalog_number, CompetitorOffer.cas, CompetitorOffer.brand_name))))
    if body.source:
        query = query.where(CompetitorOffer.source == body.source)
    if body.brand.strip():
        query = query.where(CompetitorOffer.brand_name.contains(body.brand.strip(), autoescape=True))
    if key:
        query = query.where(CompetitorOffer.id > key[0])
    found = list(db.scalars(query.order_by(CompetitorOffer.id).limit(body.limit + 1)))
    current = max(as_utc(at), as_utc(utcnow()))
    rows = [{'id': offer.id, 'product_id': offer.product_id, 'packaging_id': offer.packaging_id,
             'name': offer.name, 'article': offer.catalog_number, 'cas': offer.cas,
             'manufacturer': offer.brand_name, 'purity': None, 'packaging': offer.pack or '',
             'availability': 'unknown', 'checked_at': iso(offer.seen_at), 'product_url': None,
             'origin': 'supplier', 'fresh': offer_valid_until(db, offer) > current,
             'reason': 'Проверьте производителя, артикул и фасовку. Создайте или исправьте карточку '
                       'в каталоге и повторите проверку источника. Автоматическая публикация отключена.',
             'offers': [offer_view(db, offer)]} for offer in found[:body.limit]]
    return rows, len(found) > body.limit, [found[body.limit - 1].id] if len(found) >= body.limit else None


def handle(db: Session, body: StockIn) -> dict[str, Any]:
    now = utcnow()
    at = as_utc(body.as_of) if body.as_of else now
    if at > now + timedelta(seconds=30) or at < now - timedelta(hours=1):
        raise DomainError('STOCK_VIEW_EXPIRED', 'Обновите каталог: время формирования устарело', 422, 'as_of')
    key = read_cursor(body, at)
    rows, more, last = (catalog if body.mode == 'catalog' else review)(db, body, at, key)
    return {'as_of': iso(at), 'items': rows, 'has_more': more,
            'next_cursor': cursor_token(last, body, at) if more and last else None, 'sources': source_status(db)}


@router.post('/crm/stock')
async def stock(request: Request, db: DB) -> dict[str, Any]:
    if not settings.crm_events_secret:
        raise DomainError('CRM_EVENTS_DISABLED', 'Связь с CRM не настроена', 503)
    if not address_allowed(request.client.host if request.client else None):
        raise DomainError('CRM_ADDRESS_FORBIDDEN', 'Адрес не разрешён', 403)
    raw = await request.body()
    if len(raw) > 8192:
        raise DomainError('CRM_REQUEST_INVALID', 'Слишком большой запрос каталога', 422)
    verify({key.lower(): value for key, value in request.headers.items()}, raw)
    try:
        body = StockIn.model_validate_json(raw)
    except ValidationError:
        raise DomainError('CRM_REQUEST_INVALID', 'Запрос каталога не прошёл проверку', 422) from None
    return await run_in_threadpool(handle, db, body)
