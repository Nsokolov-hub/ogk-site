"""Лабтех: explicit stock only in the catalogue table's «Срок поставки» cell.

Observed rows have a manufacturer article and CAS in the linked title, a separate internal SKU and mostly
8–12 week delivery estimates. A price or an order button never indicates stock.
"""

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.catalog.normalize import cas_or_none
from app.catalog.stock_sources.base import Offer, Page, ParseChanged, check_answer
from app.catalog.stock_sources.html import Document, header_table, identity, links, negative, positive, tasks

ORIGIN = 'https://labteh.com'
START = f'{ORIGIN}/catalog/khimicheskie-reaktivy/'
PREFIXES = ('/catalog/khimicheskie-reaktivy/', '/catalog/standarty/')
_BRAND = r'Sigma[- ]Aldrich|Sigma|Supelco|USP|EP|EDQM|Pharmaffiliates|Pharmafiliates|Scharlau|Alpha Chemika|CDH|СDH|Macklin|Aladdin|BLDpharm|Tekkim|Dr\.? Ehrenstorfer'
_IDENTITY = re.compile(rf'(?P<brand>{_BRAND})\s+(?P<number>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:,|\(|$)', re.I)
_PACK = re.compile(r'(?:\d+\s*[xх×]\s*)?\d+(?:[.,]\d+)?\s*(?:мкг|мг|кг|г|мкл|мл|л|шт\.?|mg|kg|g|ml|l)\b', re.I)


def title_identity(title: str) -> tuple[str, str, str | None, str | None] | None:
    # Manufacturer identity precedes CAS; the final «2-xxxxx» is Лабтех's own SKU.
    head = re.split(r'\bCAS\b', title, maxsplit=1, flags=re.I)[0]
    matches = list(_IDENTITY.finditer(head))
    if not matches:
        return None
    match = matches[-1]
    cas_match = re.search(r'\bCAS\s*:?\s*(\d{2,7}-\d{2}-\d)', title, re.I)
    packs = list(_PACK.finditer(head[:match.start()]))
    return match['brand'], match['number'], cas_or_none(cas_match[1]) if cas_match else None, \
        packs[-1].group() if packs else None


def parse(page: str, url: str) -> Page:
    root = Document(page).root
    out = Page()
    found = False
    product_urls: set[str] = set()
    for headings, table_rows in header_table(root, ('наименование', 'срок поставки')):
        found = True
        item = next(i for i, value in enumerate(headings) if 'наименование' in value)
        shipping = next(i for i, value in enumerate(headings) if 'срок поставки' in value)
        price = next((i for i, value in enumerate(headings) if 'цена' in value), None)
        for row in table_rows:
            if len(row) <= max(item, shipping):
                out.incomplete = 'catalogue_table_changed'
                continue
            anchors = row[item].find('a')
            if not anchors:
                out.incomplete = 'missing_product_link'
                continue
            title = anchors[0].text()
            parsed_url = urlsplit(urljoin(url, anchors[0].attrs.get('href', '')))
            product_url = urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', ''))
            if parsed_url.netloc != urlsplit(url).netloc or not any(parsed_url.path.startswith(p) for p in PREFIXES):
                out.incomplete = 'product_link_changed'
                continue
            product_urls.add(product_url)
            available, quantity = positive(row[shipping].text())
            if not available:
                if not negative(row[shipping].text()) and quantity != 0:
                    out.incomplete = 'delivery_marker_changed'
                continue
            found_identity = title_identity(title)
            if not found_identity:
                out.incomplete = 'manufacturer_identity_missing'
                continue
            brand, number, cas, pack = found_identity
            out.offers.append(Offer(identity(product_url, number, pack), brand, number, title, product_url,
                                    cas=cas, pack=pack, quantity=quantity,
                                    price=row[price].text() if price is not None and len(row) > price else None))
    discovered = [link for link in links(root, url, PREFIXES) if link.split('?')[0] not in product_urls]
    out.tasks, out.truncated = tasks(discovered, 'labteh')
    if not found:
        raise ParseChanged('labteh_delivery_table_missing')
    return out


def page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    return parse(check_answer(client.get(task['url'])).text, task['url'])
