"""Bounded catalogue/detail checks for suppliers without a verified warehouse feed.

These sites currently expose prices and product identities, rather than a stock balance. Revisit actual linked
product pages on every run so a root-page-only check cannot hide a new public stock feed. Prices, cart buttons,
country of origin and generic company warehouse claims never become availability. A product's own structured
Offer with explicit InStock is acceptable evidence; missing manufacturer/SKU stays in manager review.
"""

import json
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlsplit

import httpx

from app.catalog.stock_sources.base import Offer, Page, check_answer
from app.catalog.stock_sources.html import Document, identity


def structured_stock(content: str, url: str) -> list[Offer]:
    """Read only Product-scoped schema.org offers, never another item's availability or an AggregateOffer."""
    root = Document(content).root
    products: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            kinds = value.get('@type', [])
            if kinds == 'Product' or isinstance(kinds, list) and 'Product' in kinds:
                products.append(value)
            if '@graph' in value:
                collect(value['@graph'])

    for script in root.find('script'):
        if script.attrs.get('type', '').casefold() != 'application/ld+json':
            continue
        try:
            collect(json.loads(''.join(child for child in script.children if isinstance(child, str))))
        except (ValueError, TypeError):
            continue
    result = []
    for product in products:
        product_url = product.get('url')
        # A carousel's unrelated Product must not supply stock to this detail URL.
        if product_url and urlsplit(urljoin(url, str(product_url)))._replace(fragment='') != \
                urlsplit(url)._replace(fragment=''):
            continue
        headings = [node.text() for node in root.find('h1')]
        if not product_url and str(product.get('name') or '') not in headings:
            continue
        offers = product.get('offers', [])
        offers = offers if isinstance(offers, list) else [offers]
        if not any(isinstance(offer, dict) and offer.get('@type') == 'Offer' and
                   offer.get('availability') in ('https://schema.org/InStock', 'http://schema.org/InStock')
                   for offer in offers):
            continue
        name = str(product.get('name') or '').strip()
        brand = product.get('brand') or product.get('manufacturer') or ''
        brand = str(brand.get('name') or '') if isinstance(brand, dict) else str(brand)
        number = str(product.get('mpn') or product.get('sku') or '').strip()
        if not name:
            continue
        pack = product.get('size')
        pack = pack.strip() if isinstance(pack, str) else None
        result.append(Offer(identity(url, number or name, pack), brand, number, name, url, pack=pack,
                            review_only=True))
    return result


def _links(content: str, current: str, allowed: Callable[[str], bool]) -> list[str]:
    found = []
    for anchor in Document(content).root.find('a'):
        url = urljoin(current, anchor.attrs.get('href', ''))
        parsed, origin = urlsplit(url), urlsplit(current)
        if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc) or parsed.username or parsed.password:
            continue
        if parsed.fragment or not allowed(url):
            continue
        if url != current and url not in found:
            found.append(url)
    return found


def _tasks(source: str, urls: list[str], depth: int) -> list[dict[str, Any]]:
    return [{'s': source, 'url': url, 'page': 1, 'probe_depth': depth} for url in urls]


def hplc_page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    url, depth = task['url'], task.get('probe_depth', 0)
    content = check_answer(client.get(url)).text
    result = Page(offers=structured_stock(content, url), incomplete='no_verified_public_stock_evidence')
    if depth == 0:
        # The public shop uses observed categoryID/productID queries, not Bitrix pagination.
        urls = _links(content, url, lambda link: urlsplit(link).path == '/index.php' and
                      dict(parse_qsl(urlsplit(link).query)) in
                      ({'categoryID': '351'}, {'categoryID': '359'}, {'categoryID': '431'}))
        result.tasks = _tasks('hplc', urls, 1)
    elif depth == 1:
        urls = _links(content, url, lambda link: urlsplit(link).path == '/index.php' and
                      bool(re.fullmatch(r'productID=\d+', urlsplit(link).query)))
        result.tasks = _tasks('hplc', urls[:3], 2)
    if result.offers:
        result.incomplete = 'public_stock_sample_requires_full_feed'
    return result


def neva_page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    url, depth = task['url'], task.get('probe_depth', 0)
    content = check_answer(client.get(url)).text
    result = Page(offers=structured_stock(content, url), incomplete='no_verified_public_stock_evidence')
    if depth == 0:
        urls = _links(content, url, lambda link: not urlsplit(link).query and urlsplit(link).path in (
            '/catalog/analiticheskie-standarty',
            '/catalog/himicheskie-reaktivy-osobo-chistye-himicheskie-veschestva-i-tehnicheskaya-himiya'))
        result.tasks = _tasks('nevareaktiv', urls, 1)
    elif depth == 1:
        urls = _links(content, url, lambda link: not urlsplit(link).query and
                      bool(re.fullmatch(r'/catalog/[^/]+/items', urlsplit(link).path)))
        result.tasks = _tasks('nevareaktiv', urls[:2], 2)
    elif depth == 2:
        urls = _links(content, url, lambda link: not urlsplit(link).query and
                      bool(re.fullmatch(r'/catalog/[^/]+/items/[^/]+', urlsplit(link).path)))
        result.tasks = _tasks('nevareaktiv', urls[:3], 3)
    if result.offers:
        result.incomplete = 'public_stock_sample_requires_full_feed'
    return result


def lenreactiv_page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    """Retry the supplied public shop after outages; inspect linked shop pages if access returns."""
    url, depth = task['url'], task.get('probe_depth', 0)
    content = check_answer(client.get(url)).text
    result = Page(offers=structured_stock(content, url), incomplete='no_verified_public_stock_evidence')
    if depth < 2:
        urls = _links(content, url, lambda link: not urlsplit(link).query and
                      urlsplit(link).path.startswith('/shop/') and
                      not re.search(r'/(?:cart|checkout|account|page)/', urlsplit(link).path))
        result.tasks = _tasks('lenreactiv', urls[:3], depth + 1)
    if result.offers:
        result.incomplete = 'public_stock_sample_requires_full_feed'
    return result
