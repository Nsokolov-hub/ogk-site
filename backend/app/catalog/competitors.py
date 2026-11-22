"""Public warehouse observations, exact product identities and expiring supplier availability.

The durable page queue runs in short worker turns. Adapters use only declared public origins/paths permitted by
current robots rules, identify as a bot and stop at refusals. A changed layout, truncated crawl or unknown stock
marker never counts as a successful empty warehouse. Explicit positive rows without a safe manufacturer/article/
packaging match remain private observations for manager review; this module never creates or publishes products.

The storefront receives only the resulting availability. Supplier names, URLs, prices, quantities and provenance
belong to admin and signed CRM responses. Fetch time and a supplier's declared stock-list date both bound the
evidence lifetime, including when crawling is disabled or a source has stopped responding.
"""

import html
import json
import logging
import re
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

import httpx
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import Brand, BrandAlias, CompetitorOffer, Packaging, Product
from app.catalog.normalize import brand_key, cas_or_none, clean_spaces, compact, parse_pack, split_pack_suffix
from app.catalog.settings import get_setting, set_setting
from app.catalog.stock_sources.base import Offer, Page, ParseChanged, PublicClient, Refused, check_answer
from app.catalog.stock_sources.registry import FIRST as EXTRA_FIRST
from app.catalog.stock_sources.registry import META as EXTRA_META
from app.catalog.stock_sources.registry import NAMES as EXTRA_NAMES
from app.catalog.stock_sources.registry import SOURCES as EXTRA_SOURCES
from app.core.config import settings
from app.core.db import as_utc, utcnow
from app.core.logs import event

logger = logging.getLogger(__name__)

# One turn of the worker: then requests to the CRM and indexing get their go.
TURN_SECONDS = 20.0
ATTEMPTS = 3
CHIMMED = 'https://chimmed-new.ru'
SKYGEN = 'https://klad.skygen.com'
# Химмед gives at most ten pages of twenty to one query; a brand with more is asked letter by letter.
CHIMMED_PAGES = 10
NAMES = {'chimmed': 'Химмед', 'skygen': 'Скайклад', **EXTRA_NAMES}
META = {
    'chimmed': {'name': 'Химмед', 'url': f'{CHIMMED}/products/storage', 'origin': CHIMMED,
                'paths': ['/products/storage', '/products/load'], 'status': 'supported'},
    'skygen': {'name': 'Скайклад', 'url': f'{SKYGEN}/catalog/', 'origin': SKYGEN,
               'paths': ['/catalog/'], 'status': 'supported'},
    **EXTRA_META,
}


def enabled() -> bool:
    flag = settings.competitor_stock_enabled
    return settings.environment == 'production' if flag is None else flag


def http_client() -> httpx.Client:
    """Replaced in tests with a client on a mock transport."""
    return httpx.Client(timeout=40, follow_redirects=False,
                        headers={'User-Agent': settings.competitor_user_agent, 'Accept-Language': 'ru'})


def pause(seconds: float) -> None:
    """Replaced in tests: no waiting between the pages."""
    time.sleep(seconds)


_answer = check_answer


# ── Химмед: «Товары в наличии» ──

def chimmed_manufacturers(page: str) -> list[str]:
    """Manufacturers of the warehouse list, from the page /products/storage (its data-letters-and-manufactors)."""
    found = re.search(r"data-letters-and-manufactors='(.*?)'", page, re.S)
    if not found:
        raise ParseChanged('chimmed: warehouse manufacturers missing')
    letters = json.loads(html.unescape(found.group(1)))
    if not isinstance(letters, dict) or any(not isinstance(groups, list) or
                                           any(not isinstance(group, list) or
                                               any(not isinstance(name, str) for name in group)
                                               for group in groups) for groups in letters.values()):
        raise ParseChanged('chimmed: invalid manufacturers')
    return [name for groups in letters.values() for group in groups for name in group if isinstance(name, str)]


def chimmed_body(maker: str, letter: str, page: int) -> dict[str, Any]:
    # The page's own request; its «perPage» is the number of the page (twenty positions each).
    return {'type': 'storage', 'filterStorage': True, 'filterPromo': False, 'filterManufactor': maker,
            'filterSubType': '', 'subType': '', 'letter': letter, 'otherType': '',
            'pagination': {'currentPage': 1, 'perPage': page}}


def chimmed_offers(data: dict[str, Any]) -> list[Offer]:
    raw = data.get('products')
    rows = raw if isinstance(raw, list) else raw.get('list') if isinstance(raw, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ParseChanged('chimmed: warehouse rows missing')
    out = []
    for row in rows:
        if not {'storage_product', 'art_number', 'id', 'manufactorName'} <= row.keys() or \
                row['storage_product'] not in (True, False, 0, 1):
            raise ParseChanged('chimmed: warehouse identity or stock marker missing')
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
        # Known brands are checked first; other positive warehouse rows belong in the private review queue.
        makers = sorted(dict.fromkeys(chimmed_manufacturers(page)), key=lambda name: not wanted(name))
        return Page(tasks=[{'s': 'chimmed', 'k': 'list', 'm': m, 'letter': '', 'page': 1} for m in makers])
    maker, letter, number = task['m'], task['letter'], task['page']
    response = _answer(client.post(f'{CHIMMED}/products/load', json=chimmed_body(maker, letter, number),
                                   headers={'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest',
                                            'Referer': f'{CHIMMED}/products/storage'}))
    data = response.json()
    if not isinstance(data, dict) or 'totalPages' not in data:
        raise ParseChanged('chimmed: warehouse pagination missing')
    out = Page(offers=chimmed_offers(data))
    if number != 1:
        return out
    pages = int(data.get('totalPages') or 1)
    letters = [str(x) for x in ((data.get('filters') or {}).get('firstLettersProducts') or [])]
    if pages >= CHIMMED_PAGES and not letter and letters:
        out.tasks = [{**task, 'letter': x, 'page': 1} for x in letters]
    else:
        out.tasks = [{**task, 'page': n} for n in range(2, min(pages, CHIMMED_PAGES) + 1)]
        out.truncated = int(pages >= CHIMMED_PAGES and (bool(letter) or not letters))
    return out


# ── Скайклад: the catalogue of warehouse goods ──

def _skygen_rows(page: str) -> tuple[list[Offer], bool]:
    from app.catalog.stock_sources.html import Document, public_url

    root = Document(page).root
    cards = [node for node in root.walk() if 'product-item' in node.attrs.get('class', '').split()]
    if not cards:
        raise ParseChanged('skygen: warehouse cards missing')
    out = []
    incomplete = False
    for card in cards:
        anchors = [node for node in card.find('a') if 'product-item-title' in node.attrs.get('class', '').split()]
        numbers = [node.text() for node in card.walk() if 'article' in node.attrs.get('class', '').split()]
        label = card.text()
        left = re.search(r'Доступно:\s*(\d+)', label, re.I)
        if (left and int(left.group(1)) == 0) or re.search(r'нет\s+в\s+наличии', label, re.I):
            continue
        if not left:
            incomplete = True
            continue
        link = anchors[0] if len(anchors) == 1 else None
        url = public_url(link.attrs.get('href', ''), f'{SKYGEN}/catalog/', ('/catalog/',)) if link else None
        identifier = re.fullmatch(r'bx_\d+_(\d+)', card.attrs.get('id', ''))
        if not link or not url or not identifier:
            incomplete = True
            continue
        makers = [node.text() for node in card.find('div') if re.match(r'^Производитель:', node.text(), re.I)]
        maker = re.sub(r'^Производитель:\s*', '', makers[-1], flags=re.I) if makers else ''
        number = numbers[0] if len(numbers) == 1 else ''
        name = link.text()[:500]
        props = re.search(r'(?:Фасовка|Упаковка|Объ[её]м):\s*([^:;]+?)(?=\s+[А-ЯA-Z][^:]*:|$)', label)
        suffix = split_pack_suffix(number, None)[1]
        size = re.search(r'(?:^|[\s,(])((?:\d+\s*[xх×]\s*)?\d+(?:[.,]\d+)?\s*'
                         r'(?:мкг|мг|кг|г|мкл|мл|л|ug|mg|kg|g|ul|ml|l|ampoules?|ампулы?|pcs|шт\.?))'
                         r'(?=\s*[,);]|\s*$)', name, re.I)
        pack = props.group(1).strip() if props else size.group(1) if size else suffix.label_en if suffix else None
        sizes = {_pack_size(value) for value in (props.group(1).strip() if props else None,
                                                 size.group(1) if size else None,
                                                 suffix.label_en if suffix else None)} - {None}
        prices = [node.text() for node in card.walk()
                  if 'product-item-price-current' in node.attrs.get('class', '').split()]
        price = re.match(r'[\d\s ,.]+руб\.', prices[0]) if prices else None
        cases = {value for raw in re.findall(r'\b\d{2,7}-\d{2}-\d\b', name) if (value := cas_or_none(raw))}
        out.append(Offer(external_id=identifier.group(1), brand_name=maker, catalog_number=number, name=name,
                         url=url, quantity=int(left.group(1)), pack=pack,
                         cas=next(iter(cases)) if len(cases) == 1 else None,
                         price=clean_spaces(price.group()) if price else None,
                         review_only=not maker or not number or len(sizes) > 1))
        incomplete |= not maker or not number
    return out, incomplete


def skygen_offers(page: str) -> list[Offer]:
    return _skygen_rows(page)[0]


def skygen_page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    number = task['page']
    response = _answer(client.get(f'{SKYGEN}/catalog/', params={'PAGEN_1': number} if number > 1 else None))
    offers, incomplete = _skygen_rows(response.text)
    out = Page(offers=offers, incomplete='skygen: incomplete warehouse card' if incomplete else None)
    last = max([int(n) for n in re.findall(r'PAGEN_1=(\d+)', response.text)] or [number])
    # Follow the visible pager one page at a time; no arbitrary 120/1000-page tail is discarded.
    if last > number:
        out.tasks = [{**task, 'page': number + 1}]
    return out


SOURCES: dict[str, Callable[[httpx.Client, dict[str, Any], Callable[[str], bool]], Page]] = {
    'chimmed': chimmed_page, 'skygen': skygen_page, **EXTRA_SOURCES}
FIRST: dict[str, dict[str, Any]] = {'chimmed': {'s': 'chimmed', 'k': 'start'},
                                   'skygen': {'s': 'skygen', 'k': 'list', 'page': 1}, **EXTRA_FIRST}


# ── their brands → ours ──

class Brands:
    """Exact normalized names and reviewed aliases; ambiguous spellings never choose a manufacturer."""

    def __init__(self, db: Session) -> None:
        choices: dict[str, set[str]] = defaultdict(set)
        for brand in db.scalars(select(Brand)):
            choices[brand_key(brand.name)].add(brand.id)
            choices[brand_key(brand.slug)].add(brand.id)
        for alias in db.scalars(select(BrandAlias)):
            choices[alias.normalized or brand_key(alias.name)].add(alias.brand_id)
        slugs = {b.slug: b.id for b in db.scalars(select(Brand))}
        reviewed = {'Agilent Technologies': 'agilent',
                    **((get_setting(db, 'competitor_stock') or {}).get('brand_aliases') or {})}
        for theirs, slug in reviewed.items():
            if slug in slugs:
                choices[brand_key(theirs)].add(slugs[slug])
        self.keys = {key: next(iter(ids)) for key, ids in choices.items() if key and len(ids) == 1}

    def find(self, name: str) -> str | None:
        return self.keys.get(brand_key(name))


# ── saving a page ──

def match(db: Session, offers: list[tuple[Offer, str]]) -> dict[int, tuple[str, str | None]]:
    """Exact brand/article identities, with CAS conflict and packaging ambiguity rejected.

    A stripped packaging suffix can identify the product only when its known fixed packagings agree. Unknown
    brands, contradictory substance identifiers and different pack sizes remain unlinked for manager review.
    """
    from app.catalog.identity import public_packagings

    by_brand: dict[str, set[str]] = defaultdict(set)
    tries: list[list[str]] = []
    for offer, brand_id in offers:
        full = compact(offer.catalog_number)
        base = compact(split_pack_suffix(offer.catalog_number, parse_pack(offer.pack))[0])
        tries.append([n for n in dict.fromkeys((full, base)) if n])
        by_brand[brand_id].update(tries[-1])
    packs: dict[tuple[str, str], list[Packaging]] = defaultdict(list)
    products: dict[tuple[str, str], Product] = {}
    by_product: dict[str, list[Packaging]] = defaultdict(list)
    candidates: dict[str, Product] = {}
    for brand_id, wanted in by_brand.items():
        for pack in db.scalars(
                select(Packaging)
                .join(Product, Product.id == Packaging.product_id)
                .where(Product.brand_id == brand_id, Packaging.catalog_number_norm.in_(wanted))):
            packs[(brand_id, str(pack.catalog_number_norm))].append(pack)
            product = db.get(Product, pack.product_id)
            if product:
                candidates[product.id] = product
        for product in db.scalars(select(Product).where(Product.brand_id == brand_id,
                                                        Product.catalog_number_norm.in_(wanted))):
            products[(brand_id, product.catalog_number_norm)] = product
            candidates[product.id] = product
    if candidates:
        for pack in db.scalars(select(Packaging).where(Packaging.product_id.in_(candidates))):
            by_product[pack.product_id].append(pack)
    approved = {product_id: public_packagings(product, by_product[product_id])
                for product_id, product in candidates.items()}
    out: dict[int, tuple[str, str | None]] = {}
    for i, ((offer, brand_id), numbers) in enumerate(zip(offers, tries, strict=True)):
        if not numbers or offer.review_only:
            continue
        exact_packs = packs.get((brand_id, numbers[0]), [])
        if exact_packs:
            if len(exact_packs) == 1:
                pack = exact_packs[0]
                product = candidates[pack.product_id]
                if pack in approved[product.id] and _cas_agrees(offer, product) and \
                        _pack_agrees(offer, pack, exact_sku=True):
                    out[i] = (product.id, pack.id)
            continue  # An ambiguous fixed SKU must not fall through to a generic product match.
        product = next((products[(brand_id, n)] for n in numbers if (brand_id, n) in products), None)
        if not product or not _cas_agrees(offer, product):
            continue
        fixed = approved[product.id]
        if not fixed:
            if not by_product[product.id]:
                out[i] = (product.id, None)
        else:
            compatible = [pack for pack in fixed if _pack_agrees(offer, pack, exact_sku=False)]
            if len(compatible) == 1:
                out[i] = (product.id, compatible[0].id)
    return out


def _cas_agrees(offer: Offer, product: Product) -> bool:
    theirs = cas_or_none(offer.cas)
    ours = {cas_or_none(c) for c in [product.cas, *(product.alt_cas or [])]} - {None}
    return not theirs or not ours or theirs in ours


_PACK_UNITS = {'ug': ('mass', Decimal('0.000001')), 'mg': ('mass', Decimal('0.001')),
               'g': ('mass', Decimal(1)), 'kg': ('mass', Decimal(1000)),
               'ul': ('volume', Decimal('0.000001')), 'ml': ('volume', Decimal('0.001')),
               'l': ('volume', Decimal(1))}


def _pack_size(raw: str | None) -> tuple[str, Decimal, int] | None:
    parsed = parse_pack(raw)
    if not parsed or not parsed.unit or parsed.amount is None:
        return None
    group, factor = _PACK_UNITS.get(parsed.unit, (parsed.unit, Decimal(1)))
    count = re.match(r'^(\d+)\s*[xх×*]', clean_spaces(raw), re.I)
    return group, parsed.amount * factor, int(count.group(1)) if count else 1


def _pack_agrees(offer: Offer, pack: Packaging, *, exact_sku: bool) -> bool:
    _base, suffix = split_pack_suffix(offer.catalog_number, parse_pack(offer.pack))
    raw = offer.pack or (suffix.label_en if suffix else None)
    theirs = _pack_size(raw)
    ours = _pack_size(pack.label_en) or _pack_size(pack.label_ru)
    if theirs and ours:
        return theirs == ours
    # The full fixed SKU is useful evidence when neither side asserts a contradictory known size.
    return exact_sku and (not raw or not ours or not theirs and compact(raw) in {
        compact(pack.label_en), compact(pack.label_ru)})


def keep_delta(db: Session) -> timedelta:
    return timedelta(days=float((get_setting(db, 'competitor_stock') or {}).get('keep_days') or 10))


def fresh_offers(db: Session, now: datetime | None = None):
    """One freshness rule for flags, admin, CRM lookup and request snapshots."""
    cutoff = (now or utcnow()) - keep_delta(db)
    return select(CompetitorOffer).where(
        CompetitorOffer.seen_at > cutoff,
        or_(CompetitorOffer.stock_updated_at.is_(None), CompetitorOffer.stock_updated_at > cutoff),
        or_(CompetitorOffer.quantity.is_(None), CompetitorOffer.quantity > 0))


def offer_valid_until(db: Session, offer: CompetitorOffer, keep: timedelta | None = None) -> datetime:
    evidence_at = as_utc(offer.seen_at)
    if offer.stock_updated_at:
        evidence_at = min(evidence_at, as_utc(offer.stock_updated_at))
    return evidence_at + (keep if keep is not None else keep_delta(db))


def _refresh_flags(db: Session, now: datetime, product_ids: set[str] | None = None) -> int:
    statement = fresh_offers(db, now).join(Packaging, Packaging.id == CompetitorOffer.packaging_id).where(
        CompetitorOffer.product_id.is_not(None), Packaging.product_id == CompetitorOffer.product_id)
    if product_ids is not None:
        if not product_ids:
            return 0
        statement = statement.where(CompetitorOffer.product_id.in_(product_ids))
    until: dict[str, datetime] = {}
    keep = keep_delta(db)
    for offer in db.scalars(statement):
        if offer.product_id:
            deadline = offer_valid_until(db, offer, keep)
            until[offer.product_id] = max(until.get(offer.product_id, deadline), deadline)
    scope = select(Product).where(or_(Product.supplier_stock, Product.id.in_(until)))
    if product_ids is not None:
        scope = scope.where(Product.id.in_(product_ids))
    gone = 0
    for product in db.scalars(scope):
        expiry = until.get(product.id)
        desired = expiry is not None
        previous_expiry = as_utc(product.supplier_stock_until) if product.supplier_stock_until else None
        if product.supplier_stock != desired or previous_expiry != expiry:
            # The search read guard needs the renewed deadline even when availability remains true.
            product.needs_index = True
        if product.supplier_stock != desired:
            gone += int(product.supplier_stock and not desired)
            product.supplier_stock = desired
        product.supplier_stock_until = expiry
    db.flush()
    return gone


def save(db: Session, source: str, offers: list[Offer], brands: Brands, now: datetime) -> tuple[int, int]:
    """(offers kept, offers matched to our products); matched products are «В наличии» at once."""
    # A connector's mistake must not publish an empty SKU, zero stock, external URL or conflicting variant.
    rejected = {o.external_id for o in offers if not _valid_offer(source, o)}
    identities: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for offer in offers:
        identities[offer.external_id].add((brand_key(offer.brand_name), compact(offer.catalog_number),
                                           clean_spaces(offer.pack).casefold()))
    ambiguous = {key for key, values in identities.items() if len(values) > 1}
    unique = list({o.external_id: o for o in offers if o.external_id not in rejected}.values())
    branded = [(o, brands.find(o.brand_name)) for o in unique]
    known: list[tuple[Offer, str]] = [(o, b) for o, b in branded
                                     if b and not o.review_only and o.external_id not in ambiguous]
    ours = {known[i][0].external_id: found for i, found in match(db, known).items()}
    existing = {row.external_id: row for row in db.scalars(select(CompetitorOffer).where(
        CompetitorOffer.source == source, CompetitorOffer.external_id.in_([o.external_id for o in offers])))}
    hits = 0
    products = {row.product_id for row in existing.values() if row.product_id}
    for key in rejected:
        if key in existing:
            db.delete(existing[key])
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
        row.stock_updated_at = offer.stock_updated_at
        row.product_id, row.packaging_id, row.seen_at = product_id, pack_id, now
        if product_id:
            hits += 1
            products.add(product_id)
    db.flush()
    _refresh_flags(db, now, products)
    return len(unique), hits


def _valid_offer(source: str, offer: Offer) -> bool:
    if not clean_spaces(offer.external_id) or not clean_spaces(offer.name or offer.catalog_number):
        return False
    if not offer.review_only and not all(clean_spaces(value) for value in (offer.catalog_number, offer.brand_name)):
        return False
    if len(offer.external_id) > 100 or len(offer.catalog_number) > 150 or len(offer.pack or '') > 120:
        return False
    if offer.quantity is not None and (not isinstance(offer.quantity, int) or
                                       isinstance(offer.quantity, bool) or offer.quantity <= 0):
        return False
    parsed = urlsplit(offer.url)
    origin = META.get(source, {}).get('origin')
    return bool(parsed.scheme in ('https', 'http') and parsed.netloc and not parsed.username and
                not parsed.password and (not origin or f'{parsed.scheme}://{parsed.netloc}' == origin))


def settle(db: Session, now: datetime, finished: Iterable[str], started: datetime) -> int:
    """A site checked to the end forgets what it did not show again; any offer older than ``keep_days`` is
    dropped; products without a fresh matched offer are no longer «В наличии». Returns the products that left."""
    cutoff = now - keep_delta(db)
    for source in finished:
        db.execute(delete(CompetitorOffer).where(CompetitorOffer.source == source, CompetitorOffer.seen_at < started))
    # A newly fetched but explicitly old list remains private evidence for review. Its declared date still makes
    # it ineligible in fresh_offers; retention is measured since we last saw the record rather than its old date.
    db.execute(delete(CompetitorOffer).where(or_(CompetitorOffer.seen_at <= cutoff,
                                               CompetitorOffer.quantity <= 0)))
    return _refresh_flags(db, now)


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
    sources = list(dict.fromkeys(s for s in (get_setting(db, 'competitor_stock') or {}).get('sources') or []
                                 if s in META))
    return {'startedAt': now.isoformat(), 'queue': [dict(FIRST[s]) for s in sources if s in FIRST and s in SOURCES],
            'scheduled': {s: [json.dumps(FIRST[s], sort_keys=True)] if s in FIRST else [] for s in sources},
            'stats': {s: {'pages': 0, 'offers': 0, 'matched': 0, 'errors': 0, 'truncated': 0, 'refused': None,
                          'incomplete': None if s in FIRST and s in SOURCES else META[s].get('reason', 'manual_source')}
                      for s in sources}}


def _enqueue(run: dict[str, Any], source: str, tasks: list[dict[str, Any]]) -> None:
    scheduled = run.setdefault('scheduled', {}).setdefault(source, [])
    keys = set(scheduled)
    for task in tasks:
        task = {key: value for key, value in task.items() if key != 'tries'}
        if task.get('s') != source:
            raise ParseChanged('cross-source task')
        key = json.dumps(task, sort_keys=True)
        if key in keys:
            continue
        scheduled.append(key)
        keys.add(key)
        run['queue'].append(task)


def _next_task(run: dict[str, Any], counts: dict[str, int], limit: int) -> dict[str, Any] | None:
    """Round-robin sources; a batch limit pauses work, never throws away discovered pages.

    A large catalogue must not monopolize the queue while other sources wait behind hundreds of its pages.
    The remaining queue and duplicate keys survive worker turns/restarts in competitor_run.
    """
    sources = list(run['stats'])
    last = run.get('lastSource')
    if last in sources:
        start_at = sources.index(last) + 1
        sources = sources[start_at:] + sources[:start_at]
    for source in sources:
        if counts.get(source, 0) >= limit:
            continue
        for index, task in enumerate(run['queue']):
            if task['s'] == source:
                run['lastSource'] = source
                counts[source] = counts.get(source, 0) + 1
                return run['queue'].pop(index)
    return None


def turn(sessions: sessionmaker[Session], seconds: float = TURN_SECONDS) -> dict[str, Any] | None:
    """One turn of the check: pages until ``seconds`` run out; the last turn settles the stock. None — nothing to do."""
    with sessions.begin() as db:
        # Freshness must continue to expire even when crawling is off, blocked, not due or indefinitely incomplete.
        settle(db, utcnow(), [], utcnow())
        if not due(db):
            return None
        run = get_setting(db, 'competitor_run') or start(db, utcnow())
        set_setting(db, 'competitor_run', run)
        pause_seconds = float((get_setting(db, 'competitor_stock') or {}).get('pause_seconds') or 2.0)
        page_limit = int((get_setting(db, 'competitor_stock') or {}).get('max_pages_per_source') or 120)
        brands = Brands(db)
    deadline = time.monotonic() + seconds
    first = True
    counts: dict[str, int] = {}
    with http_client() as client:
        clients: dict[str, PublicClient] = {}
        while run['queue'] and time.monotonic() < deadline:
            task = _next_task(run, counts, max(1, page_limit))
            if task is None:
                break
            source, stats = task['s'], run['stats'][task['s']]
            if stats['refused']:
                continue
            if not first:
                pause(pause_seconds)
            first = False
            try:
                if source not in clients:
                    meta = META[source]
                    clients[source] = PublicClient(client, str(meta['origin']), settings.competitor_user_agent,
                                                   list(meta['paths']))
                    pause(pause_seconds)
                page = SOURCES[source](clients[source], task, lambda name: brands.find(name) is not None)  # type: ignore[arg-type]
                if any(t.get('s') != source for t in page.tasks):
                    raise ParseChanged('cross-source task')
            except Refused as exc:
                reason = str(exc)
                if source in clients and reason in ('robots_disallow', 'path_not_allowed', 'redirect_loop', 'redirect_limit',
                              'redirect_requires_review', 'origin_not_allowed'):
                    # Skip this disallowed/broken link, without requesting it or erasing permitted sibling pages.
                    stats['incomplete'] = reason
                    stats['refused'] = reason if not any(t['s'] == source for t in run['queue']) else None
                else:
                    stats['refused'] = reason
                    run['queue'] = [t for t in run['queue'] if t['s'] != source]
                event(logger, 'competitor_refused', logging.WARNING, source=source, answer=str(exc))
            except ParseChanged as exc:
                stats['incomplete'] = str(exc)[:200]
                # One discontinued or incomplete card does not invalidate independent warehouse/category pages.
                event(logger, 'competitor_parser_changed', logging.WARNING, source=source, error=str(exc)[:200])
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                if task.get('tries', 0) + 1 < ATTEMPTS:
                    run['queue'].append({**task, 'tries': task.get('tries', 0) + 1})
                else:
                    stats['errors'] += 1
                event(logger, 'competitor_page_failed', logging.WARNING, source=source, error=str(exc)[:200])
            else:
                with sessions.begin() as db:
                    kept, hits = save(db, source, page.offers, brands, utcnow())
                    _enqueue(run, source, page.tasks)
                    stats['pages'] += 1
                    stats['offers'] += kept
                    stats['matched'] += hits
                    stats['truncated'] += page.truncated
                    if page.incomplete:
                        stats['incomplete'] = page.incomplete
                    set_setting(db, 'competitor_run', run)
                continue
            with sessions.begin() as db:
                set_setting(db, 'competitor_run', run)
    if run['queue']:
        return run
    with sessions.begin() as db:
        now = utcnow()
        finished = [s for s, st in run['stats'].items() if not st['refused'] and not st['errors']
                    and not st['truncated'] and not st.get('incomplete')]
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
    rows = db.execute(fresh_offers(db).with_only_columns(CompetitorOffer.source, CompetitorOffer.product_id)
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
    in_stock = db.scalar(select(func.count()).select_from(Product).where(
        Product.supplier_stock, Product.supplier_stock_until > utcnow())) or 0
    review = db.scalar(select(func.count()).select_from(fresh_offers(db).where(
        or_(CompetitorOffer.product_id.is_(None), CompetitorOffer.packaging_id.is_(None))).subquery())) or 0
    return {'enabled': enabled(), 'settings': get_setting(db, 'competitor_stock'), 'last': results or None,
            'running': {'startedAt': run['startedAt'], 'left': len(run['queue']), 'stats': run['stats']} if run else None,
            'productsInStock': int(in_stock), 'pendingReview': int(review), 'names': NAMES, 'sources': META}


def offers_of(db: Session, product_id: str, now: datetime | None = None) -> list[dict[str, Any]]:
    rows = db.scalars(fresh_offers(db, now).where(CompetitorOffer.product_id == product_id)
                      .order_by(CompetitorOffer.source, CompetitorOffer.seen_at.desc()))
    return [{'source': r.source, 'sourceName': NAMES.get(r.source, r.source), 'name': r.name,
             'catalogNumber': r.catalog_number, 'pack': r.pack, 'quantity': r.quantity, 'price': r.price, 'url': r.url,
             'packagingId': r.packaging_id, 'seenAt': as_utc(r.seen_at).isoformat(),
             'stockUpdatedAt': as_utc(r.stock_updated_at).isoformat() if r.stock_updated_at else None,
             'validUntil': offer_valid_until(db, r).isoformat()} for r in rows]
