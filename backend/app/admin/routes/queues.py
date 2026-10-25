"""Queues of the catalog manager (ADM-05): moderation, CAS conflicts, new manufacturers from imports, «обогатить»
by demand, demand without a product, disputed controlled substances, products without a category."""

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.admin.audit import record
from app.admin.models import ProductDemand
from app.admin.security import StaffDep, requires
from app.catalog import brands_sync
from app.catalog.models import Brand, ImportIssue, Product, ProductCategory, SearchMiss
from app.catalog.normalize import cas_or_none
from app.catalog.service import refresh_card
from app.core.db import DB, utcnow
from app.core.errors import DomainError

router = APIRouter()
DEMAND_DAYS = 90


def new_brands_statement() -> Any:
    """Brands an import created that nobody has looked at: no CRM entry, no page, not merged."""
    return select(Brand).where(Brand.crm_manufacturer_id.is_(None), Brand.page_published.is_(False),
                               Brand.merged_into_id.is_(None),
                               Brand.id.in_(select(ImportIssue.values['brand_id'].as_string())
                                            .where(ImportIssue.code == 'BRAND_CREATED', ImportIssue.resolved.is_(False))))


@router.get('/queues', dependencies=[requires('queues.read')])
def summary(db: DB) -> dict[str, int]:
    since = utcnow() - timedelta(days=30)
    return {
        'moderation': db.scalar(select(func.count()).select_from(Product).where(Product.status == 'moderation')) or 0,
        'conflicts': db.scalar(select(func.count()).select_from(ImportIssue).where(
            ImportIssue.kind == 'conflict', ImportIssue.resolved.is_(False))) or 0,
        'brands': db.scalar(select(func.count()).select_from(new_brands_statement().subquery())) or 0,
        'controlled': db.scalar(select(func.count()).select_from(Product).where(
            Product.controlled_state == 'review')) or 0,
        'misses': db.scalar(select(func.count()).select_from(SearchMiss).where(SearchMiss.last_at >= since)) or 0,
        'noCategory': db.scalar(select(func.count()).select_from(Product).where(
            ~select(ProductCategory.product_id).where(ProductCategory.product_id == Product.id).exists())) or 0,
    }


@router.get('/queues/conflicts', dependencies=[requires('queues.read')])
def conflicts(db: DB, page: int = 1) -> dict[str, Any]:
    statement = select(ImportIssue).where(ImportIssue.kind == 'conflict', ImportIssue.resolved.is_(False))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(db.scalars(statement.order_by(ImportIssue.id.desc()).offset((max(page, 1) - 1) * 50).limit(50)))
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(
        [r.product_id for r in rows if r.product_id])))}
    return {'total': total, 'items': [{
        'id': r.id, 'message': r.message, 'values': r.values, 'productId': r.product_id,
        'product': f'{products[r.product_id].catalog_number} — {products[r.product_id].name_en}'
        if r.product_id in products else None,
        'currentCas': products[r.product_id].cas if r.product_id in products else None} for r in rows]}


class ResolveIn(BaseModel):
    action: str


@router.post('/queues/conflicts/{issue_id}', dependencies=[requires('queues.write')])
def resolve_conflict(issue_id: int, body: ResolveIn, staff: StaffDep, db: DB) -> dict[str, bool]:
    """keep — CAS карточки верный; apply — верный CAS из прайса (ручная правка, импорт его больше не тронет)."""
    issue = db.get(ImportIssue, issue_id)
    if issue is None or issue.kind != 'conflict':
        raise DomainError('NOT_FOUND', 'Конфликт не найден', 404)
    if body.action == 'apply' and issue.product_id:
        product = db.get(Product, issue.product_id)
        cas = cas_or_none(str((issue.values or {}).get('cas') or ''))
        if product is None or cas is None:
            raise DomainError('VALUE_INVALID', 'В строке прайса нет корректного CAS', 422)
        before = product.cas
        product.cas = cas
        product.manual_fields = sorted(set(product.manual_fields or []) | {'cas'})
        refresh_card(db, product)
        record(db, staff, 'product', product.id, 'cas_conflict', f'{product.catalog_number}: CAS {before} → {cas}')
    elif body.action != 'keep':
        raise DomainError('ACTION_INVALID', 'Действие: keep или apply', 422, 'action')
    issue.resolved = True
    return {'ok': True}


@router.get('/queues/brands', dependencies=[requires('queues.read')])
def new_brands(db: DB) -> dict[str, Any]:
    rows = list(db.scalars(new_brands_statement().order_by(Brand.name).limit(500)))
    counts = dict(db.execute(select(Product.brand_id, func.count()).where(Product.brand_id.in_([b.id for b in rows]))
                             .group_by(Product.brand_id)).all()) if rows else {}
    return {'items': [{'id': b.id, 'name': b.name, 'slug': b.slug, 'count': counts.get(b.id, 0)} for b in rows]}


class BrandDecisionIn(BaseModel):
    action: str
    targetId: str | None = None


@router.post('/queues/brands/{brand_id}', dependencies=[requires('queues.write')])
def decide_brand(brand_id: str, body: BrandDecisionIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    """keep — отдельный производитель; merge — это написание другого бренда: товары и написания переходят к нему."""
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise DomainError('NOT_FOUND', 'Бренд не найден', 404)
    moved = 0
    if body.action == 'merge':
        target = db.get(Brand, body.targetId) if body.targetId else None
        if target is None or target.id == brand.id:
            raise DomainError('VALUE_INVALID', 'Выберите бренд, в который объединить', 422, 'targetId')
        moved = brands_sync.merge(db, brand, target)
        record(db, staff, 'brand', brand.id, 'merge', f'{brand.name} → {target.name}: товаров {moved}')
    elif body.action == 'keep':
        record(db, staff, 'brand', brand.id, 'reviewed', brand.name)
    else:
        raise DomainError('ACTION_INVALID', 'Действие: keep или merge', 422, 'action')
    for issue in db.scalars(select(ImportIssue).where(ImportIssue.code == 'BRAND_CREATED',
                                                      ImportIssue.values['brand_id'].as_string() == brand.id)):
        issue.resolved = True
    db.flush()
    return {'moved': moved}


@router.get('/queues/enrich', dependencies=[requires('queues.read')])
def enrich(db: DB, page: int = 1) -> dict[str, Any]:
    """Опубликованные карточки ниже порога индексации — сначала самые востребованные (ТЗ 5.6)."""
    since = date.today() - timedelta(days=DEMAND_DAYS)
    demand = (select(ProductDemand.product_id, (func.sum(ProductDemand.views) + 10 * func.sum(ProductDemand.requests))
                     .label('score'), func.sum(ProductDemand.views).label('views'),
                     func.sum(ProductDemand.requests).label('requests'))
              .where(ProductDemand.day >= since).group_by(ProductDemand.product_id).subquery())
    statement = (select(Product, demand.c.score, demand.c.views, demand.c.requests)
                 .join(demand, demand.c.product_id == Product.id)
                 .where(Product.status == 'published', Product.indexable.is_(False)))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(statement.order_by(demand.c.score.desc()).offset((max(page, 1) - 1) * 50).limit(50)).all()
    return {'total': total, 'items': [{'id': p.id, 'catalogNumber': p.catalog_number, 'name': p.name_en,
                                       'completeness': p.completeness, 'views': int(views or 0),
                                       'requests': int(requests or 0)} for p, _, views, requests in rows]}


@router.get('/queues/misses', dependencies=[requires('queues.read')])
def misses(db: DB, days: int = 30) -> dict[str, Any]:
    """Спрос без товара (SRCH-12): запросы без результатов — источник для пополнения каталога."""
    since = utcnow() - timedelta(days=max(1, min(days, 365)))
    rows = db.execute(select(SearchMiss.query, SearchMiss.lang, func.sum(SearchMiss.count), func.max(SearchMiss.last_at))
                      .where(SearchMiss.last_at >= since).group_by(SearchMiss.query, SearchMiss.lang)
                      .order_by(func.sum(SearchMiss.count).desc()).limit(200)).all()
    return {'items': [{'query': q, 'lang': lang, 'count': int(n), 'lastAt': last.isoformat()}
                      for q, lang, n, last in rows]}


@router.get('/queues/controlled', dependencies=[requires('queues.read')])
def controlled(db: DB) -> dict[str, Any]:
    rows = db.scalars(select(Product).where(Product.controlled_state == 'review').order_by(Product.name_en).limit(200))
    return {'items': [{'id': p.id, 'catalogNumber': p.catalog_number, 'name': p.name_en, 'cas': p.cas,
                       'list': p.controlled} for p in rows]}


class ControlledIn(BaseModel):
    decision: str


@router.post('/queues/controlled/{product_id}', dependencies=[requires('queues.write')])
def decide_controlled(product_id: str, body: ControlledIn, staff: StaffDep, db: DB) -> dict[str, bool]:
    """Решение химика (ТЗ 5.2.1): confirmed — подконтрольное, скрыто; cleared — не подконтрольное."""
    product = db.get(Product, product_id)
    if product is None:
        raise DomainError('NOT_FOUND', 'Товар не найден', 404)
    if body.decision not in ('confirmed', 'cleared'):
        raise DomainError('ACTION_INVALID', 'Решение: confirmed или cleared', 422, 'decision')
    product.controlled_state = body.decision
    if body.decision == 'cleared':
        product.controlled = None
    refresh_card(db, product)
    record(db, staff, 'product', product.id, f'controlled_{body.decision}', product.catalog_number)
    return {'ok': True}
