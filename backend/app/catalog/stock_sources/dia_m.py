"""Диаэм: public product tables, inspected 20 November 2026.

The reactive index itself promises only that *most* goods are stocked. Only an individual table row with
«Наличие на складе» and «В наличии» is evidence. Transit and recommendation blocks are never stock offers.
"""

import re
from collections.abc import Callable
from typing import Any

import httpx

from app.catalog.normalize import cas_or_none, parse_pack
from app.catalog.stock_sources.base import Offer, Page, ParseChanged, check_answer
from app.catalog.stock_sources.html import Document, header_table, identity, links, negative, positive, tasks

ORIGIN = 'https://www.dia-m.ru'
START = f'{ORIGIN}/catalog/reactive/'
PREFIXES = ('/catalog/reactive/',)


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
    out = Page()
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
    discovered = links(root, url, PREFIXES)
    # Product tables contain all variants; recommendation links after them are intentionally not crawled.
    if not found:
        out.tasks, out.truncated = tasks(discovered, 'diam')
        if not title or not discovered:
            raise ParseChanged('dia_m_catalogue_or_product_table_missing')
    return out


def page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    return parse(check_answer(client.get(task['url'])).text, task['url'])
