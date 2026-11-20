"""Вилакс: quantities in a single product card, never generic warehouse prose.

The spreadsheet's old chromatography category is empty; its visible Welch navigation leads to the active
column catalogue. Public cards explicitly distinguish «Есть в наличии: 3» from «Нет в наличии».
"""

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.catalog.stock_sources.base import Offer, Page, ParseChanged, check_answer
from app.catalog.stock_sources.html import Document, Node, identity, links, public_url, tasks

ORIGIN = 'https://vilax.ru'
START = f'{ORIGIN}/catalog/oborudovanie_i_materialy/kolonki_khromatograficheskie/'
PREFIXES = ('/catalog/oborudovanie_i_materialy/welch/',
            '/catalog/oborudovanie_i_materialy/kolonki_khromatograficheskie/')
_TITLE = re.compile(r'^(\S+(?:\s+Chemika)?)\s+([A-Za-z0-9][A-Za-z0-9._-]*)\s+(.+)$', re.I)
_STOCK = re.compile(r'Есть\s+в\s+наличии\s*:\s*(\d+)', re.I)


def product_title(anchor: Node):
    match = _TITLE.match(anchor.text())
    return match if match and any(char.isdigit() for char in match[2]) else None


def parse(page: str, url: str) -> Page:
    root = Document(page).root
    out = Page()
    products = [(anchor, match) for anchor in root.find('a') if (match := product_title(anchor))]
    seen: set[str] = set()
    for anchor, match in products:
        product_url = public_url(anchor.attrs.get('href', ''), url, PREFIXES)
        if not product_url or product_url in seen:
            continue
        seen.add(product_url)
        scope = anchor.parent
        marker = None
        for _ in range(7):
            if scope is None:
                break
            local_urls = {public_url(candidate.attrs.get('href', ''), url, PREFIXES)
                          for candidate in scope.find('a') if product_title(candidate)} - {None}
            if len(local_urls) > 1:
                break
            marker = _STOCK.search(scope.text())
            if marker or re.search(r'Нет\s+в\s+наличии', scope.text(), re.I):
                break
            scope = scope.parent
        if not marker:
            # A recognized product card with no local availability must not clear older stock.
            if scope and not re.search(r'Нет\s+в\s+наличии', scope.text(), re.I):
                out.incomplete = 'card_stock_marker_missing'
            continue
        quantity = int(marker[1])
        if quantity <= 0:
            continue
        # Read after the availability count, so «3» units cannot become the first digit of the price.
        price = re.search(r'[\d][\d\s\xa0.,]*\s*(?:₽|руб\.)', scope.text()[marker.end():]) if scope else None
        out.offers.append(Offer(identity(product_url, match[2]), match[1], match[2], anchor.text(), product_url,
                                quantity=quantity, price=price.group().strip() if price else None))
    # Listing cards provide complete identity and quantity. Follow categories/pagination, not every detail page.
    discovered = [link for link in links(root, url, PREFIXES)
                  if not re.search(r'/\d+/$', urlsplit(link).path)]
    out.tasks, out.truncated = tasks(discovered, 'vilax')
    if not products:
        if 'Не нашли товары в разделе' in root.text() and discovered:
            out.incomplete = 'requested_category_empty_using_public_navigation'
        else:
            raise ParseChanged('vilax_product_cards_missing')
    return out


def page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    return parse(check_answer(client.get(task['url'])).text, task['url'])
