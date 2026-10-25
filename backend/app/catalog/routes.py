"""Public catalog API (TZ 12.2): /api/v1/public/catalog, products, brands, substances, search and the cart.

Only published data; controlled products are hidden while the setting says so (TZ 5.2.1). Search answers are
limited per address and in depth (NFR-05).
"""

import hmac
import io
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy import select

from app.catalog import pages
from app.catalog import schemas as s
from app.catalog.importer.reader import UnreadableFile, read_rows
from app.catalog.models import Cart
from app.catalog.search import query as search
from app.catalog.search.documents import FACET_FIELDS
from app.catalog.search.engine import SearchEngine
from app.catalog.search.meili import engine as meili_engine
from app.core.config import settings
from app.core.db import DB, utcnow
from app.core.errors import DomainError
from app.core.ratelimit import RateLimiter

router = APIRouter(prefix='/public', tags=['Каталог'])
Lang = Annotated[Literal['ru', 'en'], Query()]
CACHE = 'public, max-age=60, stale-while-revalidate=300'
CART_COOKIE = 'ogk_cart'
CART_DAYS = 90


def get_engine() -> SearchEngine:
    return meili_engine()


Engine = Annotated[SearchEngine, Depends(get_engine)]


limiter = RateLimiter('search')


def limited(request: Request) -> None:
    """Search and listings per visitor (NFR-05). The storefront's own cached requests carry the shared secret and
    are not counted: they serve every visitor at once; requests it makes for one visitor carry the visitor's
    address in X-Forwarded-For and are counted for that visitor."""
    token = request.headers.get('x-site-token', '')
    if token and settings.revalidate_secret and hmac.compare_digest(token, settings.revalidate_secret):
        return
    if not limiter.allow(request.client.host if request.client else 'unknown', settings.search_rate_per_minute):
        raise DomainError('RATE_LIMITED', 'Слишком много запросов. Повторите через минуту', 429)


def cached(response: Response) -> None:
    response.headers['Cache-Control'] = CACHE


def facet_params(request: Request, prefix: str) -> dict[str, list[str]]:
    """Filters as repeated query parameters: f.brand=waters&f.pack=100-mg; values may be comma-separated."""
    out: dict[str, list[str]] = {}
    for key, value in request.query_params.multi_items():
        if key.startswith(prefix) and key[len(prefix):] in FACET_FIELDS:
            out.setdefault(key[len(prefix):], []).extend(v for v in value.split(',') if v)
    return out


# ── catalog ──

@router.get('/catalog/tree', response_model=list[s.CategoryNode])
def catalog_tree(db: DB, response: Response):
    cached(response)
    return pages.tree(db)


@router.get('/catalog/category', response_model=s.CategoryOut)
def catalog_category(db: DB, response: Response, path: str = ''):
    found = pages.category(db, path.strip('/'))
    if found is None:
        raise DomainError('NOT_FOUND', 'Раздел не найден', 404)
    cached(response)
    return found


@router.get('/catalog/listing', response_model=s.CatalogListing, dependencies=[Depends(limited)])
def catalog_listing(request: Request, db: DB, engine: Engine, response: Response, lang: Lang = 'ru',
                    path: str = '', sort: Literal['popular', 'name'] = 'popular',
                    page: Annotated[int, Query(ge=1)] = 1, pageSize: Annotated[int, Query(ge=1, le=96)] = 24,
                    facets: str = ''):
    cached(response)
    keys = [k for k in facets.split(',') if k in FACET_FIELDS]
    return search.listing(db, engine, path=path.strip('/'), filters=facet_params(request, 'f.'),
                          preset=facet_params(request, 'p.'), sort=sort, page=page, page_size=pageSize,
                          facet_keys=keys, lang=lang)


@router.get('/catalog/count', response_model=s.CountOut)
def catalog_count(request: Request, engine: Engine, response: Response, path: str = ''):
    cached(response)
    return {'count': search.count(engine, path.strip('/'), facet_params(request, 'p.'))}


@router.get('/catalog/brands', response_model=list[s.CategoryBrand])
def catalog_brands(request: Request, db: DB, engine: Engine, response: Response, path: str = ''):
    cached(response)
    return search.brands_in(db, engine, path.strip('/'), facet_params(request, 'p.'))


@router.get('/catalog/popular', response_model=s.ProductsPage)
def catalog_popular(db: DB, engine: Engine, response: Response, lang: Lang = 'ru',
                    sort: Literal['popular', 'alpha'] = 'popular', offset: Annotated[int, Query(ge=0, le=200)] = 0,
                    limit: Annotated[int, Query(ge=1, le=48)] = 12, path: str = ''):
    """The home page block and «Часто заказывают»: the most popular products, 36 at most."""
    cached(response)
    top = search.listing(db, engine, path=path.strip('/'), filters={}, preset={}, sort='popular', page=1,
                         page_size=36, facet_keys=[], lang=lang)
    items = top['items']
    if sort == 'alpha':
        items = sorted(items, key=lambda p: p['name'].casefold())
    return {'items': items[offset:offset + limit], 'total': len(items)}


@router.get('/catalog/sitemap', response_model=s.SitemapPage)
def catalog_sitemap(db: DB, response: Response, page: Annotated[int, Query(ge=1)] = 1):
    cached(response)
    return pages.sitemap(db, page)


@router.get('/catalog/feed', response_model=s.FeedOut)
def catalog_feed(db: DB, response: Response):
    cached(response)
    return pages.feed(db)


@router.get('/products/{slug}', response_model=s.ProductPage)
def product(slug: str, db: DB, response: Response, lang: Lang = 'ru'):
    found = pages.product_page(db, slug, lang)
    if not found.get('product') and not found.get('moved'):
        raise DomainError('NOT_FOUND', 'Товар не найден', 404)
    cached(response)
    return found


@router.get('/substances', response_model=list[s.SubstanceListItem])
def substance_list(db: DB, response: Response):
    cached(response)
    return pages.substances(db)


@router.get('/substances/{slug}', response_model=s.SubstancePage)
def substance(slug: str, db: DB, response: Response, lang: Lang = 'ru'):
    found = pages.substance_page(db, slug, lang)
    if not found.get('substance') and not found.get('moved'):
        raise DomainError('NOT_FOUND', 'Субстанция не найдена', 404)
    cached(response)
    return found


@router.get('/brands', response_model=list[s.BrandOut])
def brand_list(db: DB, response: Response):
    cached(response)
    return pages.brands(db)


@router.get('/brands/{slug}', response_model=s.BrandPage)
def brand(slug: str, db: DB, response: Response, lang: Lang = 'ru'):
    found = pages.brand_page(db, slug, lang)
    if not found.get('brand') and not found.get('moved'):
        raise DomainError('NOT_FOUND', 'Бренд не найден', 404)
    cached(response)
    return found


# ── search ──

@router.get('/search/suggest', response_model=s.SuggestResult, dependencies=[Depends(limited)])
def suggest(db: DB, engine: Engine, response: Response, q: Annotated[str, Query(max_length=100)] = '',
            lang: Lang = 'ru'):
    cached(response)
    return search.suggest(db, engine, q, lang)


@router.get('/search', response_model=s.SearchPageResult, dependencies=[Depends(limited)])
def search_page(db: DB, engine: Engine, q: Annotated[str, Query(max_length=200)] = '', brand: str | None = None,
                category: str | None = None, page: Annotated[int, Query(ge=1)] = 1, lang: Lang = 'ru'):
    return search.search_page(db, engine, query=q, brand=brand, category=category, page=page, lang=lang)


@router.post('/search/batch', response_model=s.BatchOut, dependencies=[Depends(limited)])
def search_batch(body: s.BatchIn, engine: Engine):
    lines = [line for line in body.lines if line.strip()]
    return {'lines': search.batch(engine, lines, body.lang), 'truncated': len(lines) > search.BATCH_LIMIT}


MAX_LIST_FILE = 2 * 1024 * 1024


@router.post('/search/batch/file', response_model=s.BatchOut, dependencies=[Depends(limited)])
def search_batch_file(engine: Engine, file: Annotated[UploadFile, File()], lang: Annotated[Literal['ru', 'en'],
                                                                                           Query()] = 'ru'):
    """A list from xlsx or csv (SC-02): each row's filled cells form a line «запрос [количество]»."""
    data = file.file.read(MAX_LIST_FILE + 1)
    if len(data) > MAX_LIST_FILE:
        raise DomainError('FILE_TOO_LARGE', 'Файл больше 2 МБ', 413, 'file')
    lines: list[str] = []
    try:
        for row in read_rows(io.BytesIO(data), file.filename or ''):
            cells = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
            if cells:
                lines.append('\t'.join(cells))
            if len(lines) > search.BATCH_LIMIT + 1:
                break
    except UnreadableFile as exc:
        raise DomainError('FILE_UNREADABLE', str(exc), 422, 'file') from exc
    # A header row («Кат. №», «Количество») finds nothing and stays a free line the customer can delete.
    return {'lines': search.batch(engine, lines, lang), 'truncated': len(lines) > search.BATCH_LIMIT}


# ── the cart of a guest (RFQ-01) ──

def _cart_id(request: Request) -> str | None:
    value = request.cookies.get(CART_COOKIE, '')
    return value if len(value) == 36 else None


@router.get('/cart', response_model=s.CartOut)
def cart_get(request: Request, db: DB):
    cart_id = _cart_id(request)
    row = db.get(Cart, cart_id) if cart_id else None
    return {'items': row.items if row else [], 'updatedAt': row.updated_at.isoformat() if row else None}


@router.put('/cart', response_model=s.CartOut)
def cart_put(body: s.CartIn, request: Request, response: Response, db: DB):
    cart_id = _cart_id(request)
    row = db.scalar(select(Cart).where(Cart.id == cart_id).with_for_update()) if cart_id else None
    if row is None:
        row = Cart(id=str(uuid4()), items=[])
        db.add(row)
    row.items = body.items
    row.updated_at = utcnow()
    db.flush()
    response.set_cookie(CART_COOKIE, row.id, max_age=CART_DAYS * 86400, httponly=True, samesite='lax',
                        secure=settings.site_url.startswith('https://') and settings.environment == 'production')
    return {'items': row.items, 'updatedAt': row.updated_at.isoformat()}
