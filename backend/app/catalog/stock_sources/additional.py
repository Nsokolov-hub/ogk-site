"""Additional public sources from the business's November stock list.

Only explicit warehouse evidence becomes an offer. A site without public stock evidence remains visible as a
source needing confirmation; neither a price nor a buy button is a warehouse declaration.
"""

import io
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from app.catalog.normalize import cas_or_none
from app.catalog.stock_sources.base import Offer, Page, ParseChanged, check_answer
from app.catalog.stock_sources.html import Document, header_table, identity

ALGIMED = 'https://algimed.ru/news/algimed-stocks-of-reagents-and-standard-samples/'
CSDB = 'https://www.csdb.ru/price/price_chem.pdf'
_MONTHS = dict(zip(('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
                    'сентября', 'октября', 'ноября', 'декабря'), range(1, 13), strict=True))
_PACK = re.compile(r'(?:\d+\s*[xх×]\s*)?\d+(?:[.,]\d+)?\s*(?:мкг|мг|кг|г|мкл|мл|л|шт\.?|mg|kg|g|ml|l)\b', re.I)


def algimed_parse(content: str) -> Page:
    root = Document(content).root
    title = root.find('h1')
    if not title or 'складские остатки' not in title[0].text().casefold():
        raise ParseChanged('algimed_warehouse_page_changed')
    stamp = re.search(r'Актуализация\s*:?\s*(\d{1,2})\s+(\w+)\s+(\d{4})', root.text(), re.I)
    if not stamp or stamp[2].casefold() not in _MONTHS:
        raise ParseChanged('algimed_stock_date_missing')
    updated = datetime(int(stamp[3]), _MONTHS[stamp[2].casefold()], int(stamp[1]), tzinfo=UTC)
    result = Page()
    tables = list(header_table(root, ('номенклатура', 'количество')))
    if not tables:
        raise ParseChanged('algimed_stock_table_missing')
    for _headers, rows in tables:
        brand = ''
        for row in rows:
            if len(row) == 1 and row[0].attrs.get('colspan') == '2':
                brand = row[0].text()
                continue
            if len(row) != 2:
                result.incomplete = 'algimed_stock_row_changed'
                continue
            name, quantity = row[0].text(), row[1].text()
            if not re.fullmatch(r'\d+', quantity):
                result.incomplete = 'algimed_stock_quantity_changed'
                continue
            if int(quantity) <= 0:
                continue
            article = name.rsplit(',', 1)[-1].strip(' ).;')
            if not brand or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/+-]{0,149}', article):
                result.incomplete = 'algimed_manufacturer_article_missing'
                continue
            packs = list(_PACK.finditer(name))
            pack = packs[-1].group() if packs else None
            result.offers.append(Offer(identity(ALGIMED, brand + '|' + article, pack), brand, article, name, ALGIMED,
                                       pack=pack, quantity=int(quantity), stock_updated_at=updated))
    return result


def algimed_page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    return algimed_parse(check_answer(client.get(ALGIMED)).text)


def csdb_text(content: str) -> list[dict[str, Any]]:
    """The observed PDF uses a stable fixed-width layout; dates mean incoming goods, only СПБ means warehouse."""
    lines = content.splitlines()
    header = next((line for line in lines if 'Наименование' in line and 'Базовая уп.' in line
                   and 'Наличие на' in line and 'Перейти' in line), None)
    if not header:
        raise ParseChanged('csdb_price_columns_changed')
    name_end, cas_start, link_start = header.index('ГОСТ'), header.index('CAS'), header.index('Перейти')
    pack_start, pack_end, stock_start = header.index('Базовая уп.'), header.index('1 кг'), header.index('Наличие на')
    result: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    continuations = 0
    for line in lines:
        if re.search(r'\bперейти\b', line[link_start:pack_start], re.I) and 'Наименование' not in line:
            pack_match = re.search(r'\(([^()]+)\)', line[pack_start:pack_end])
            current = {'name': line[:name_end].strip(), 'cas': cas_or_none(line[cas_start:link_start].strip()),
                       'pack': pack_match[1] if pack_match else None, 'stock': line[stock_start:].strip()}
            result.append(current)
            continuations = 0
        elif current is not None and continuations < 2 and line[:name_end].strip() and \
                not line[pack_start:stock_start].strip() and 'Цены указаны' not in line:
            # Multi-line chemical names stay together; other columns such as ГОСТ are not guessed as names.
            current['name'] += ' ' + line[:name_end].strip()
            continuations += 1
        elif line.strip():
            current = None
    return result


def csdb_parse(content: bytes) -> Page:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    if len(content) > 5_000_000 or not content.startswith(b'%PDF-'):
        raise ParseChanged('csdb_pdf_invalid')
    try:
        reader = PdfReader(io.BytesIO(content))
        if not 1 <= len(reader.pages) <= 50:
            raise ParseChanged('csdb_pdf_page_count_changed')
        result = Page(incomplete='manufacturer_and_article_require_manager_review')
        for pdf_page in reader.pages:
            text = pdf_page.extract_text(extraction_mode='layout')
            rows = csdb_text(text)
            urls = [str(annotation.get_object().get('/A', {}).get('/URI') or '')
                    for annotation in pdf_page.get('/Annots', [])]
            urls = [url for url in urls if url.startswith('https://www.csdb.ru/shop/')]
            if len(rows) != len(urls):
                raise ParseChanged('csdb_pdf_product_links_changed')
            stamp = re.search(r'Цены указаны[^\n]*\bна\s+(\d{2})\.(\d{2})\.(\d{2}|\d{4})\b', text)
            if not stamp:
                raise ParseChanged('csdb_price_date_missing')
            year = int(stamp[3]) + (2000 if len(stamp[3]) == 2 else 0)
            updated = datetime(year, int(stamp[2]), int(stamp[1]), tzinfo=UTC)
            for row, url in zip(rows, urls, strict=True):
                if row['stock'].casefold() not in ('спб', 'санкт-петербург') or not row['name']:
                    continue
                # This supplier's PDF has no manufacturer SKU. Never relabel its CAS/retail ID as one.
                result.offers.append(Offer(identity(url, '', row['pack']), '', '', row['name'], url,
                                          cas=row['cas'], pack=row['pack'], stock_updated_at=updated,
                                          review_only=True))
        return result
    except ParseChanged:
        raise
    except (ValueError, TypeError, KeyError, IndexError, PdfReadError) as exc:
        raise ParseChanged('csdb_pdf_layout_changed') from exc


def csdb_page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    return csdb_parse(check_answer(client.get(CSDB)).content)


def needs_evidence(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    response = check_answer(client.get(task['url']))
    if not Document(response.text).root.text():
        raise ParseChanged('public_page_empty')
    return Page(incomplete='no_verified_public_stock_evidence')


NAMES = {'algimed': 'Альгимед', 'csdb': 'Химические решения (ЦСДБ)', 'hplc': 'Элсико / HPLC.ru',
         'nevareaktiv': 'НеваРеактив', 'lenreactiv': 'ЛенРеактив'}
META = {
    'algimed': {'name': NAMES['algimed'], 'url': ALGIMED, 'origin': 'https://algimed.ru', 'paths': ['/news/'],
                'status': 'supported', 'reason': 'Публичная складская таблица; дата актуализации ограничивает свежесть'},
    'csdb': {'name': NAMES['csdb'], 'url': CSDB, 'origin': 'https://www.csdb.ru', 'paths': ['/price/'],
             'status': 'review_only', 'reason': 'PDF: только СПБ; производитель и артикул требуют проверки менеджером'},
    'hplc': {'name': NAMES['hplc'], 'url': 'https://www.shop.hplc.ru/', 'origin': 'https://www.shop.hplc.ru',
             'paths': ['/'], 'status': 'needs_verification',
             'reason': 'В открытой карточке есть артикул, но нет подтверждённого складского остатка'},
    'nevareaktiv': {'name': NAMES['nevareaktiv'], 'url': 'https://www.nevareaktiv.ru/',
                    'origin': 'https://www.nevareaktiv.ru', 'paths': ['/'], 'status': 'needs_verification',
                    'reason': 'Открытый каталог не подтверждает наличие конкретной фасовки'},
    'lenreactiv': {'name': NAMES['lenreactiv'], 'url': 'https://lenreactiv.ru/shop/',
                   'origin': 'https://lenreactiv.ru', 'paths': ['/shop/'], 'status': 'temporarily_unavailable',
                   'reason': 'Проверка 20.11.2026: HTTP 503. Требуется повторная доступная проверка или файл остатков'},
}
SOURCES = {'algimed': algimed_page, 'csdb': csdb_page, 'hplc': needs_evidence,
           'nevareaktiv': needs_evidence, 'lenreactiv': needs_evidence}
FIRST = {code: {'s': code, 'url': data['url'], 'page': 1} for code, data in META.items()}
