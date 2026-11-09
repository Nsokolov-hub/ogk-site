"""Stock of suppliers: what chimmed-new.ru and klad.skygen.com have in their warehouses (09.11.2026).

Why: a customer who does not see «В наличии» with us goes to look elsewhere. A position a supplier keeps in stock we
can buy there and ship with our margin, so our card says «В наличии» too (Product.supplier_stock). What none of them
has stays «Под заказ».

What is read: only the public lists of warehouse goods that robots.txt of each site allows — Химмед's «Товары в
наличии» (/products/storage and its POST /products/load, under the allowed /products/*) and Скайклад's catalogue
(/catalog/ and its pages ?PAGEN_1=N). Never their search, accounts or carts. One request at a time with a pause
(``pause_seconds``), and the check says it is a bot. A site that refuses (403, 429, a captcha) is left alone until the
next check: its refusal is reported in the admin panel, never worked around.

How: a check is a queue of pages. The worker takes short turns (TURN_SECONDS) so requests to the CRM and indexing keep
flowing; the queue lives in the setting ``competitor_run``, and a restart continues it. Every page is saved at once:
offers are matched to our products by brand and catalog number (also with the packaging cut off the number,
«413283-100G» → «413283»), and the matched products get supplier_stock. A site checked to the end drops its offers
not seen again; a site that could not be checked keeps its offers for ``keep_days``, then they no longer count.
"""

import html
import json
import logging
import re
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import Brand, BrandAlias, CompetitorOffer, Packaging, Product
from app.catalog.normalize import brand_key, cas_or_none, clean_spaces, compact, parse_pack, split_pack_suffix
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.core.db import utcnow
from app.core.logs import event

logger = logging.getLogger(__name__)

# One turn of the worker: then requests to the CRM and indexing get their go.
TURN_SECONDS = 20.0
ATTEMPTS = 3
CHIMMED = 'https://chimmed-new.ru'
SKYGEN = 'https://klad.skygen.com'
# Химмед gives at most ten pages of twenty to one query; a brand with more is asked letter by letter.
CHIMMED_PAGES = 10
NAMES = {'chimmed': 'Химмед', 'skygen': 'Скайклад'}


class Refused(Exception):
    """The site does not want the check now (403, 429, a captcha): leave it until the next check."""


def enabled() -> bool:
    flag = settings.competitor_stock_enabled
    return settings.environment == 'production' if flag is None else flag


def http_client() -> httpx.Client:
    """Replaced in tests with a client on a mock transport."""
    return httpx.Client(timeout=40, follow_redirects=True,
                        headers={'User-Agent': settings.competitor_user_agent, 'Accept-Language': 'ru'})


def pause(seconds: float) -> None:
    """Replaced in tests: no waiting between the pages."""
    time.sleep(seconds)


# ── what one page gives ──

@dataclass
class Offer:
    external_id: str
    brand_name: str
    catalog_number: str
    name: str
    url: str
    cas: str | None = None
    pack: str | None = None
    quantity: int | None = None
    price: str | None = None


@dataclass
class Page:
    offers: list[Offer] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    # A query that had more positions than the site shows (Химмед's ten pages of one letter).
    truncated: int = 0


def _answer(response: httpx.Response) -> httpx.Response:
    if response.status_code in (403, 429, 451) or response.status_code == 503 and 'captcha' in response.text.lower():
        raise Refused(f'{response.status_code}')
    if response.status_code >= 400:
        raise httpx.HTTPStatusError(f'HTTP {response.status_code}', request=response.request, response=response)
    head = response.text[:4000].lower()
    if 'captcha' in head and ('<form' in head or 'smartcaptcha' in head):
        raise Refused('captcha')
    return response


# ── Химмед: «Товары в наличии» ──

def chimmed_manufacturers(page: str) -> list[str]:
    """Manufacturers of the warehouse list, from the page /products/storage (its data-letters-and-manufactors)."""
    found = re.search(r"data-letters-and-manufactors='(.*?)'", page, re.S)
    if not found:
        return []
    letters = json.loads(html.unescape(found.group(1)))
    return [name for groups in letters.values() for group in groups for name in group if isinstance(name, str)]


def chimmed_body(maker: str, letter: str, page: int) -> dict[str, Any]:
    # The page's own request; its «perPage» is the number of the page (twenty positions each).
    return {'type': 'storage', 'filterStorage': True, 'filterPromo': False, 'filterManufactor': maker,
            'filterSubType': '', 'subType': '', 'letter': letter, 'otherType': '',
            'pagination': {'currentPage': 1, 'perPage': page}}


def chimmed_offers(data: dict[str, Any]) -> list[Offer]:
    raw = data.get('products')
    rows = raw if isinstance(raw, list) else (raw or {}).get('list') or [] if isinstance(raw, dict) else []
    out = []
    for row in rows:
        number = clean_spaces(str(row.get('art_number') or ''))
        if not row.get('storage_product') or not number or not row.get('id'):
            continue
        slug = str(row.get('url') or '').strip('/')
        out.append(Offer(external_id=str(row['id']), brand_name=clean_spaces(str(row.get('manufactorName') or '')),
                         catalog_number=number, name=clean_spaces(str(row.get('name') or '')).strip('"; .')[:500],
                         url=f'{CHIMMED}/products/{slug}-id={row["id"]}' if slug else f'{CHIMMED}/products/storage',
                         cas=cas_or_none(row.get('cas')), pack=clean_spaces(str(row.get('packing') or '')) or None,
                         price=clean_spaces(str(row.get('price') or '')) or None))
    return out


def chimmed_page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    if task['k'] == 'start':
        page = _answer(client.get(f'{CHIMMED}/products/storage')).text
        makers = [m for m in chimmed_manufacturers(page) if wanted(m)]
        return Page(tasks=[{'s': 'chimmed', 'k': 'list', 'm': m, 'letter': '', 'page': 1} for m in makers])
    maker, letter, number = task['m'], task['letter'], task['page']
    response = _answer(client.post(f'{CHIMMED}/products/load', json=chimmed_body(maker, letter, number),
                                   headers={'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest',
                                            'Referer': f'{CHIMMED}/products/storage'}))
    data = response.json()
    out = Page(offers=chimmed_offers(data))
    if number != 1:
        return out
    pages = int(data.get('totalPages') or 1)
    letters = [str(x) for x in ((data.get('filters') or {}).get('firstLettersProducts') or [])]
    if pages >= CHIMMED_PAGES and not letter and letters:
        out.tasks = [{**task, 'letter': x, 'page': 1} for x in letters]
    else:
        out.tasks = [{**task, 'page': n} for n in range(2, min(pages, CHIMMED_PAGES) + 1)]
        out.truncated = int(pages >= CHIMMED_PAGES and bool(letter))
    return out


# ── Скайклад: the catalogue of warehouse goods ──

_CARD = re.compile(r'<div class="product-item" id="bx_\d+_(?P<id>\d+)">(?P<body>.*?)</form>', re.S)


def _text(fragment: str) -> str:
    return clean_spaces(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)))


def skygen_offers(page: str) -> list[Offer]:
    out = []
    for card in _CARD.finditer(page):
        body = card.group('body')
        link = re.search(r'<a href="(/catalog/[^"]+)" class="product-item-title[^"]*">(.*?)</a>', body, re.S)
        number = re.search(r'<div class="article">(.*?)</div>', body, re.S)
        maker = re.search(r'Производитель:\s*(.*?)</div>', body, re.S)
        left = re.search(r'Доступно:\s*(\d+)', body)
        if not (link and number and maker and left) or int(left.group(1)) <= 0:
            continue
        price = re.search(r'product-item-price-current[^>]*>\s*([\d\s ,.]+руб\.)', body)
        out.append(Offer(external_id=card.group('id'), brand_name=_text(maker.group(1)),
                         catalog_number=_text(number.group(1)), name=_text(link.group(2))[:500],
                         url=f'{SKYGEN}{link.group(1)}', quantity=int(left.group(1)),
                         price=clean_spaces(price.group(1)) if price else None))
    return out


def skygen_page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    number = task['page']
    page = _answer(client.get(f'{SKYGEN}/catalog/', params={'PAGEN_1': number} if number > 1 else None)).text
    out = Page(offers=[o for o in skygen_offers(page) if wanted(o.brand_name)])
    if number == 1:
        last = max([int(n) for n in re.findall(r'PAGEN_1=(\d+)', page)] or [1])
        out.tasks = [{**task, 'page': n} for n in range(2, last + 1)]
    return out


SOURCES: dict[str, Callable[[httpx.Client, dict[str, Any], Callable[[str], bool]], Page]] = {
    'chimmed': chimmed_page, 'skygen': skygen_page}
FIRST: dict[str, dict[str, Any]] = {'chimmed': {'s': 'chimmed', 'k': 'start'},
                                   'skygen': {'s': 'skygen', 'k': 'list', 'page': 1}}


# ── their brands → ours ──

class Brands:
    """Our brands by the spellings of the suppliers: the name, its aliases, the setting ``brand_aliases``, and «Agilent
    Technologies» for «Agilent» (one name starts with the other, at least four letters)."""

    def __init__(self, db: Session) -> None:
        self.keys: dict[str, str] = {}
        for brand in db.scalars(select(Brand)):
            self.keys[brand_key(brand.name)] = brand.id
            self.keys.setdefault(brand_key(brand.slug), brand.id)
        for alias in db.scalars(select(BrandAlias)):
            self.keys.setdefault(alias.normalized or brand_key(alias.name), alias.brand_id)
        slugs = {b.slug: b.id for b in db.scalars(select(Brand))}
        for theirs, slug in ((get_setting(db, 'competitor_stock') or {}).get('brand_aliases') or {}).items():
            if slug in slugs:
                self.keys[brand_key(theirs)] = slugs[slug]
        self.cache: dict[str, str | None] = {}

    def find(self, name: str) -> str | None:
        key = brand_key(name)
        if key not in self.cache:
            found = self.keys.get(key)
            if found is None and len(key) >= 4:
                near = [(len(k), b) for k, b in self.keys.items() if len(k) >= 4 and (key.startswith(k) or k.startswith(key))]
                found = max(near)[1] if near else None
            self.cache[key] = found
        return self.cache[key]


# ── saving a page ──

def match(db: Session, offers: list[tuple[Offer, str]]) -> dict[int, tuple[str, str | None]]:
    """Index of the offer → (our product, our packaging) by brand and catalog number: the packaging's full number,
    then the product's, then the product's number without the packaging at its end."""
    by_brand: dict[str, set[str]] = defaultdict(set)
    tries: list[list[str]] = []
    for offer, brand_id in offers:
        full = compact(offer.catalog_number)
        base = compact(split_pack_suffix(offer.catalog_number, parse_pack(offer.pack))[0])
        tries.append([n for n in dict.fromkeys((full, base)) if n])
        by_brand[brand_id].update(tries[-1])
    packs: dict[tuple[str, str], tuple[str, str]] = {}
    products: dict[tuple[str, str], str] = {}
    for brand_id, wanted in by_brand.items():
        for pack_id, product_id, pack_norm in db.execute(
                select(Packaging.id, Packaging.product_id, Packaging.catalog_number_norm)
                .join(Product, Product.id == Packaging.product_id)
                .where(Product.brand_id == brand_id, Packaging.catalog_number_norm.in_(wanted))):
            packs[(brand_id, str(pack_norm))] = (product_id, pack_id)
        for product_id, norm in db.execute(select(Product.id, Product.catalog_number_norm)
                                           .where(Product.brand_id == brand_id,
                                                  Product.catalog_number_norm.in_(wanted))):
            products[(brand_id, norm)] = product_id
    out: dict[int, tuple[str, str | None]] = {}
    for i, ((_offer, brand_id), numbers) in enumerate(zip(offers, tries, strict=True)):
        if (brand_id, numbers[0]) in packs:
            out[i] = packs[(brand_id, numbers[0])]
            continue
        product = next((products[(brand_id, n)] for n in numbers if (brand_id, n) in products), None)
        if product:
            out[i] = (product, None)
    return out


def save(db: Session, source: str, offers: list[Offer], brands: Brands, now: datetime) -> tuple[int, int]:
    """(offers kept, offers matched to our products); matched products are «В наличии» at once."""
    unique = list({o.external_id: o for o in offers}.values())
    branded = [(o, brands.find(o.brand_name)) for o in unique]
    known: list[tuple[Offer, str]] = [(o, b) for o, b in branded if b]
    ours = {known[i][0].external_id: found for i, found in match(db, known).items()}
    existing = {row.external_id: row for row in db.scalars(select(CompetitorOffer).where(
        CompetitorOffer.source == source, CompetitorOffer.external_id.in_([o.external_id for o in unique])))}
    hits = 0
    products: set[str] = set()
    for offer, brand_id in branded:
        product_id, pack_id = ours.get(offer.external_id) or (None, None)
        row = existing.get(offer.external_id)
        if row is None:
            row = CompetitorOffer(source=source, external_id=offer.external_id, first_seen_at=now)
            db.add(row)
        row.brand_name, row.brand_id = offer.brand_name[:250], brand_id
        row.catalog_number, row.catalog_number_norm = offer.catalog_number[:150], compact(offer.catalog_number)[:150]
        row.name, row.cas, row.pack = offer.name or offer.catalog_number, offer.cas, (offer.pack or None)
        row.quantity, row.price, row.url = offer.quantity, (offer.price or '')[:60] or None, offer.url[:500]
        row.product_id, row.packaging_id, row.seen_at = product_id, pack_id, now
        if product_id:
            hits += 1
            products.add(product_id)
    if products:
        db.execute(update(Product).where(Product.id.in_(products), ~Product.supplier_stock)
                   .values(supplier_stock=True, needs_index=True).execution_options(synchronize_session=False))
    db.flush()
    return len(unique), hits


def settle(db: Session, now: datetime, finished: Iterable[str], started: datetime) -> int:
    """A site checked to the end forgets what it did not show again; any offer older than ``keep_days`` is
    dropped; products without a fresh matched offer are no longer «В наличии». Returns the products that left."""
    keep = timedelta(days=float((get_setting(db, 'competitor_stock') or {}).get('keep_days') or 10))
    for source in finished:
        db.execute(delete(CompetitorOffer).where(CompetitorOffer.source == source, CompetitorOffer.seen_at < started))
    db.execute(delete(CompetitorOffer).where(CompetitorOffer.seen_at < now - keep))
    fresh = exists().where(CompetitorOffer.product_id == Product.id)
    # Only the few flagged products are looked at (partial index ix_products_supplier_stock).
    gone = db.execute(update(Product).where(Product.supplier_stock, ~fresh)
                      .values(supplier_stock=False, needs_index=True).execution_options(synchronize_session=False))
    # And back: a matched offer whose product lost the flag (e.g. a turn failed between saving and flagging).
    db.execute(update(Product).where(Product.id.in_(select(CompetitorOffer.product_id)
                                                   .where(CompetitorOffer.product_id.is_not(None))),
                                     ~Product.supplier_stock)
               .values(supplier_stock=True, needs_index=True).execution_options(synchronize_session=False))
    return int(getattr(gone, 'rowcount', 0) or 0)


# ── the check, in turns ──

def due(db: Session, now: datetime | None = None) -> bool:
    if not enabled():
        return False
    if get_setting(db, 'competitor_run'):
        return True
    every = timedelta(days=float((get_setting(db, 'competitor_stock') or {}).get('every_days') or 3))
    last = (get_setting(db, 'competitor_results') or {}).get('finishedAt')
    return not last or (now or utcnow()) - datetime.fromisoformat(last) >= every


def start(db: Session, now: datetime) -> dict[str, Any]:
    sources = [s for s in (get_setting(db, 'competitor_stock') or {}).get('sources') or [] if s in SOURCES]
    return {'startedAt': now.isoformat(), 'queue': [dict(FIRST[s]) for s in sources],
            'stats': {s: {'pages': 0, 'offers': 0, 'matched': 0, 'errors': 0, 'truncated': 0, 'refused': None}
                      for s in sources}}


def turn(sessions: sessionmaker[Session], seconds: float = TURN_SECONDS) -> dict[str, Any] | None:
    """One turn of the check: pages until ``seconds`` run out; the last turn settles the stock. None — nothing to do."""
    with sessions.begin() as db:
        if not due(db):
            return None
        run = get_setting(db, 'competitor_run') or start(db, utcnow())
        set_setting(db, 'competitor_run', run)
        pause_seconds = float((get_setting(db, 'competitor_stock') or {}).get('pause_seconds') or 2.0)
        brands = Brands(db)
    deadline = time.monotonic() + seconds
    first = True
    with http_client() as client:
        while run['queue'] and time.monotonic() < deadline:
            task = run['queue'].pop(0)
            source, stats = task['s'], run['stats'][task['s']]
            if stats['refused']:
                continue
            if not first:
                pause(pause_seconds)
            first = False
            try:
                page = SOURCES[source](client, task, lambda name: brands.find(name) is not None)
            except Refused as exc:
                stats['refused'] = str(exc)
                run['queue'] = [t for t in run['queue'] if t['s'] != source]
                event(logger, 'competitor_refused', logging.WARNING, source=source, answer=str(exc))
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                if task.get('tries', 0) + 1 < ATTEMPTS:
                    run['queue'].append({**task, 'tries': task.get('tries', 0) + 1})
                else:
                    stats['errors'] += 1
                event(logger, 'competitor_page_failed', logging.WARNING, source=source, error=str(exc)[:200])
            else:
                with sessions.begin() as db:
                    kept, hits = save(db, source, page.offers, brands, utcnow())
                    run['queue'] += page.tasks
                    stats['pages'] += 1
                    stats['offers'] += kept
                    stats['matched'] += hits
                    stats['truncated'] += page.truncated
                    set_setting(db, 'competitor_run', run)
                continue
            with sessions.begin() as db:
                set_setting(db, 'competitor_run', run)
    if run['queue']:
        return run
    with sessions.begin() as db:
        now = utcnow()
        finished = [s for s, st in run['stats'].items() if not st['refused'] and not st['errors']]
        gone = settle(db, now, finished, datetime.fromisoformat(run['startedAt']))
        products = _count_products(db)
        result = {'startedAt': run['startedAt'], 'finishedAt': now.isoformat(), 'left': gone,
                  'sources': {s: {**st, 'products': products.get(s, 0), 'complete': s in finished}
                              for s, st in run['stats'].items()}}
        set_setting(db, 'competitor_results', result)
        set_setting(db, 'competitor_run', None)
    event(logger, 'competitor_checked', left=gone, **{s: st['matched'] for s, st in run['stats'].items()})
    return result


def _count_products(db: Session) -> dict[str, int]:
    rows = db.execute(select(CompetitorOffer.source, CompetitorOffer.product_id)
                      .where(CompetitorOffer.product_id.is_not(None)).distinct()).all()
    out: dict[str, int] = defaultdict(int)
    for source, _product in rows:
        out[source] += 1
    return dict(out)


def run_all(sessions: sessionmaker[Session]) -> dict[str, Any] | None:
    """The whole check at once (`cli competitors`): turns until the queue is empty."""
    result = None
    while True:
        step = turn(sessions, seconds=3600)
        if step is None or 'finishedAt' in step:
            return step or result
        result = step


# ── for the admin panel ──

def status(db: Session) -> dict[str, Any]:
    run = get_setting(db, 'competitor_run')
    results = get_setting(db, 'competitor_results') or {}
    in_stock = db.scalar(select(func.count()).select_from(Product).where(Product.supplier_stock)) or 0
    return {'enabled': enabled(), 'settings': get_setting(db, 'competitor_stock'), 'last': results or None,
            'running': {'startedAt': run['startedAt'], 'left': len(run['queue']), 'stats': run['stats']} if run else None,
            'productsInStock': int(in_stock), 'names': NAMES}


def offers_of(db: Session, product_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(select(CompetitorOffer).where(CompetitorOffer.product_id == product_id)
                      .order_by(CompetitorOffer.source, CompetitorOffer.seen_at.desc()))
    return [{'source': r.source, 'sourceName': NAMES.get(r.source, r.source), 'name': r.name,
             'catalogNumber': r.catalog_number, 'pack': r.pack, 'quantity': r.quantity, 'price': r.price, 'url': r.url,
             'packagingId': r.packaging_id, 'seenAt': r.seen_at.isoformat()} for r in rows]
