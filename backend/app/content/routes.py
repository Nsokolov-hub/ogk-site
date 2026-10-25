"""Public texts of the site (ADM-02, ADM-07, ADM-10): pages, SEO landings, contacts and requisites, redirects.

The storefront caches them with the tags ``content`` and ``landings``; publishing in the admin panel drops the
cache. ``?preview=`` with a signed link from the admin panel shows the draft of exactly that page, never cached.
"""

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.admin.editables import preview_data
from app.admin.models import ContentPage, ProductDemand, Redirect, SeoLanding
from app.catalog.models import Product
from app.catalog.settings import get_setting
from app.core.db import DB
from app.core.errors import DomainError
from app.core.ratelimit import RateLimiter

router = APIRouter(prefix='/public', tags=['Контент'])
CACHE = 'public, max-age=60, stale-while-revalidate=300'
Kind = Literal['home', 'service', 'solution', 'article', 'author', 'trust']
views_limiter = RateLimiter('views')


def cached(response: Response, preview: bool = False) -> None:
    response.headers['Cache-Control'] = 'no-store' if preview else CACHE


@router.get('/site')
def site(db: DB, response: Response) -> dict[str, Any]:
    """Контакты и реквизиты (RU и EN), счётчики, шаблоны метатегов, дополнение robots.txt."""
    cached(response)
    counters = get_setting(db, 'counters') or {}
    return {**get_setting(db, 'site'), 'counters': {'ym': counters.get('ym'), 'ga': counters.get('ga')},
            'metaTemplates': get_setting(db, 'meta_templates'), 'robotsExtra': get_setting(db, 'robots_extra') or ''}


def page_out(row: ContentPage, content: dict[str, Any] | None = None) -> dict[str, Any]:
    return {'kind': row.kind, 'slug': row.slug, 'position': row.position, 'content': content or row.content,
            'updatedAt': row.updated_at.isoformat() if row.updated_at else None}


@router.get('/pages')
def page_list(db: DB, response: Response, kind: Kind) -> list[dict[str, Any]]:
    """Опубликованные страницы одного вида — для списков /services/, /articles/, /solutions/ и Sitemap."""
    cached(response)
    rows = db.scalars(select(ContentPage).where(ContentPage.kind == kind, ContentPage.status == 'published')
                      .order_by(ContentPage.position, ContentPage.slug))
    return [page_out(row) for row in rows]


@router.get('/pages/{kind}/{slug}')
def page(kind: Kind, slug: str, db: DB, response: Response, preview: str | None = None) -> dict[str, Any]:
    row = db.scalar(select(ContentPage).where(ContentPage.kind == kind, ContentPage.slug == slug))
    draft = preview_data(db, preview, 'page', row.id) if row is not None else None
    if row is None or (row.status != 'published' and draft is None):
        moved = db.scalar(select(Redirect.target).where(Redirect.source == page_path(kind, slug)))
        if moved:
            cached(response)
            return {'moved': moved}
        raise DomainError('NOT_FOUND', 'Страница не найдена', 404)
    cached(response, preview=draft is not None)
    return {**page_out(row, draft.get('content') if draft else None), 'preview': draft is not None}


def page_path(kind: str, slug: str) -> str:
    return {'home': '/', 'service': f'/services/{slug}/', 'solution': f'/solutions/{slug}/',
            'article': f'/articles/{slug}/', 'author': f'/authors/{slug}/', 'trust': f'/{slug}/'}[kind]


def landing_out(row: SeoLanding, data: dict[str, Any] | None = None) -> dict[str, Any]:
    source = data or {'categoryPath': row.category_path, 'slug': row.slug, 'filters': row.filters,
                      'content': row.content, 'position': row.position}
    return {'id': row.id, 'parent': source['categoryPath'], 'slug': source['slug'], 'preset': source['filters'],
            'position': source.get('position', row.position), 'content': source['content'],
            'updatedAt': row.updated_at.isoformat() if row.updated_at else None}


@router.get('/landings')
def landings(db: DB, response: Response, path: str | None = None) -> list[dict[str, Any]]:
    """SEO-посадочные (URL-07): все опубликованные или посадочные одного раздела."""
    cached(response)
    statement = select(SeoLanding).where(SeoLanding.status == 'published')
    if path is not None:
        statement = statement.where(SeoLanding.category_path == path.strip('/'))
    return [landing_out(row) for row in db.scalars(statement.order_by(SeoLanding.position, SeoLanding.slug))]


@router.get('/landing')
def landing(db: DB, response: Response, path: str, slug: str, preview: str | None = None) -> dict[str, Any]:
    row = db.scalar(select(SeoLanding).where(SeoLanding.category_path == path.strip('/'), SeoLanding.slug == slug))
    draft = preview_data(db, preview, 'landing', row.id) if row is not None else None
    if row is None or (row.status != 'published' and draft is None):
        raise DomainError('NOT_FOUND', 'Посадочная не найдена', 404)
    cached(response, preview=draft is not None)
    return {**landing_out(row, draft), 'preview': draft is not None}


@router.get('/redirects')
def redirects(db: DB, response: Response) -> list[dict[str, Any]]:
    """Редиректы из админки (ADM-07): витрина применяет их до рендера страницы."""
    cached(response)
    return [{'source': r.source, 'target': r.target, 'code': r.code}
            for r in db.scalars(select(Redirect).order_by(Redirect.source))]


@router.post('/products/{slug}/view', status_code=204, include_in_schema=False)
@router.post('/products/{slug}/view/', status_code=204, include_in_schema=False)
def product_view(slug: str, request: Request, db: DB) -> Response:
    """Просмотр карточки для очереди «обогатить» по спросу (TZ 5.6); витрина шлёт его раз за сеанс."""
    if views_limiter.allow(request.client.host if request.client else 'unknown', 60):
        product_id = db.scalar(select(Product.id).where(Product.slug == slug))
        if product_id:
            count_demand(db, product_id, views=1)
    return Response(status_code=204)


def count_demand(db: Session, product_id: str, *, views: int = 0, requests: int = 0) -> None:
    values = {'product_id': product_id, 'day': date.today(), 'views': views, 'requests': requests}
    if db.get_bind().dialect.name == 'postgresql':
        statement: Any = pg_insert(ProductDemand).values(**values)
    else:
        statement = sqlite_insert(ProductDemand).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=['product_id', 'day'],
        set_={'views': ProductDemand.views + views, 'requests': ProductDemand.requests + requests})
    db.execute(statement)
