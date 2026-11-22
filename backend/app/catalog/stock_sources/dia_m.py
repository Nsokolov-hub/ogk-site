"""Диаэм: public product tables and catalogue variant cards, inspected 22 November 2026.

The reactive index itself promises only that *most* goods are stocked. Only an individual table row with
«Наличие на складе» and «В наличии», or the same variant's explicit status tooltip, is evidence. Transit and
recommendation blocks are never stock offers.
"""

import re
from collections.abc import Callable
from typing import Any

import httpx

from app.catalog.normalize import cas_or_none, parse_pack
from app.catalog.stock_sources.base import Offer, Page, ParseChanged, check_answer
from app.catalog.stock_sources.html import (
    Document,
    Node,
    header_table,
    identity,
    links,
    negative,
    positive,
    public_url,
    tasks,
)

ORIGIN = 'https://www.dia-m.ru'
START = f'{ORIGIN}/catalog/reactive/'
PREFIXES = ('/catalog/reactive/',)


def _class(node: Node, name: str) -> bool:
    return name in node.attrs.get('class', '').split()


def catalogue_cards(root: Node, url: str) -> tuple[Page, set[str]]:
    """The current alphabet/category pages include every variant with a local stock tooltip.

    Do not fetch thousands of detail pages to rediscover the same variants, or use the category's generic
    warehouse heading as a stock marker. Manufacturer, article, pack and availability belong to one model.
    """
    out = Page()
    complete: set[str] = set()
    for card in root.find('article'):
        if not _class(card, 'product-card'):
            continue
        models = [node for node in card.walk() if _class(node, 'product-model')]
        if not models:
            continue  # Older cards and «См. ...» cross references still need their observed detail link.
        anchors = [node for node in card.find('a') if _class(node, 'product-card__name')]
        if len(anchors) != 1:
            out.incomplete = 'catalogue_card_identity_changed'
            continue
        product_url = public_url(anchors[0].attrs.get('href', ''), url, PREFIXES)
        if not product_url:
            out.incomplete = 'catalogue_card_link_changed'
            continue
        title = anchors[0].text()
        complete.add(product_url)
        for model in models:
            statuses = [node for node in model.walk() if _class(node, 'product-model__status')]
            if len(statuses) != 1:
                out.incomplete = 'catalogue_card_stock_changed'
                complete.discard(product_url)
                continue
            marker = statuses[0].attrs.get('title', '') or statuses[0].text()
            available, quantity = positive(marker)
            if not available:
                if not negative(marker) and quantity != 0:
                    out.incomplete = 'stock_marker_changed'
                    complete.discard(product_url)
                continue
            numbers = [node.text() for node in model.walk() if _class(node, 'product-model__article')]
            number = numbers[0] if len(numbers) == 1 else ''
            brand = model.attrs.get('data-manufacturer', '').strip()
            if not number or not brand or (model.attrs.get('data-value') and model.attrs['data-value'] != number):
                out.incomplete = 'catalogue_card_identity_changed'
                complete.discard(product_url)
                continue
            packs = [node.text() for node in model.walk() if _class(node, 'product-model__amount')]
            pack = packs[0] if len(packs) == 1 else None
            prices = [node.text() for node in model.walk() if _class(node, 'product-model__price')]
            cases = {value for candidate in re.findall(r'\b\d{2,7}-\d{2}-\d\b', card.text())
                     if (value := cas_or_none(candidate))}
            out.offers.append(Offer(identity(product_url, number, pack), brand, number, title, product_url,
                                    cas=next(iter(cases)) if len(cases) == 1 else None, pack=pack,
                                    quantity=quantity, price=prices[0] if prices else None))
    return out, complete


def parse(page: str, url: str) -> Page:
    root = Document(page).root
    heading = root.find('h1')
    title = heading[0].text() if heading else ''
    # On real product pages the last H1 link names the manufacturer. Earlier text may name analogues.
    brands = heading[0].find('a') if heading else []
    brand = brands[-1].text() if brands else ''
    cas_match = re.search(r'\b\d{2,7}-\d{2}-\d\b', title)
    cas = cas_or_none(cas_match.group()) if cas_match else None
    in_product = False
    for node in root.walk():
        if heading and node is heading[0]:
            in_product = True
        elif in_product:
            label = node.text().casefold()
            if node.tag == 'aside' or label in {'с этим товаром покупают', 'рекомендуем'}:
                break
            if node.tag == 'table' and ('cas-no' in label or 'cas номер' in label):
                match = re.search(r'\b\d{2,7}-\d{2}-\d\b', node.text())
                cas = cas or (cas_or_none(match.group()) if match else None)
    out, complete_cards = catalogue_cards(root, url)
    found = False
    # The main variants precede «Описание». Recommendation widgets later in the document may also contain
    # warehouse tables, and must never inherit the primary product's manufacturer or CAS.
    main_tables = []
    in_product = False
    for node in root.walk():
        if heading and node is heading[0]:
            in_product = True
        elif in_product:
            label = node.text().casefold()
            if node.tag == 'aside' or label in {'с этим товаром покупают', 'рекомендуем'} or \
                    (node.tag in {'h2', 'h3', 'h4', 'h5', 'h6'}
                     and any(word in label for word in ('описание', 'каталоги', 'оплата', 'доставка', 'рекомендуем'))):
                break
            if node.tag == 'table':
                main_tables.append(node)
    for headings, table_rows in header_table(root, ('артикул', 'наличие на складе'), main_tables):
        found = True
        article = next(i for i, item in enumerate(headings) if 'артикул' in item)
        stock = next(i for i, item in enumerate(headings) if 'наличие на складе' in item)
        price = next((i for i, item in enumerate(headings) if 'цена' in item), None)
        for row in table_rows:
            if len(row) <= max(article, stock):
                out.incomplete = 'product_table_changed'
                continue
            available, quantity = positive(row[stock].text())
            if not available:
                if not negative(row[stock].text()) and quantity != 0:
                    out.incomplete = 'stock_marker_changed'
                continue
            number = row[article].text()
            if not number:
                out.incomplete = 'missing_manufacturer_article'
                continue
            if not brand:
                out.incomplete = 'manufacturer_brand_missing'
                continue
            pack = next((cell.text() for cell in row[article + 1:price if price is not None else stock]
                         if (parsed := parse_pack(cell.text())) and parsed.unit), None)
            out.offers.append(Offer(identity(url, number, pack), brand, number, title, url, cas=cas,
                                    pack=pack, quantity=quantity,
                                    price=row[price].text() if price is not None and len(row) > price else None))
    discovered = [link for link in links(root, url, PREFIXES) if link not in complete_cards]
    # Prefer remaining detail links to the alphabet/header repeated on every index page.
    product_links = {public_url(anchor.attrs.get('href', ''), url, PREFIXES)
                     for anchor in root.find('a') if _class(anchor, 'product-card__name')}
    # Alphabet pages already contain variants; visit those before the deeper generic category tree.
    discovered.sort(key=lambda link: (link not in product_links, '/letter-' not in link))
    # Product tables contain all variants; recommendation links after them are intentionally not crawled.
    if not found:
        out.tasks, out.truncated = tasks(discovered, 'diam')
        if not title or (not discovered and not complete_cards):
            raise ParseChanged('dia_m_catalogue_or_product_table_missing')
    return out


def page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    return parse(check_answer(client.get(task['url'])).text, task['url'])
