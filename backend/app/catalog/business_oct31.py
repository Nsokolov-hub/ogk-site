"""Business remarks of 31 October 2026 on the catalog.

* «Лабораторное оборудование» goes: cheap, not worth selling or buying traffic for.
* «Посуда и тара» and other glassware and consumables go; filters stay (they live in chromatography/filters).
* The USP–NF Online subscription is no longer sold.
* Precursors of List IV of Decree No. 681 are not supplied: see seed/controlled-register.json.

The changes of the texts are exact: a text edited in the admin panel since the seed stays as it is.
"""

import csv
import gzip
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

REMOVED_CATEGORIES = ('laboratory-equipment', 'laboratory-glassware')
REDIRECTS = {
    '/catalog/laboratory-equipment/': '/catalog/',
    '/catalog/laboratory-glassware/': '/catalog/chromatography/filters/',
}
NOT_SOLD = re.compile(r'usp\s*[-–—]?\s*nf\b.*\b(online|subscription|подписк)', re.I)

# Texts that offered equipment or glassware → the same texts without them (seed wording, ru and en).
TEXTS = {
    'Материалы, реактивы и оборудование для фармацевтических лабораторий':
        'Стандартные образцы, реактивы и расходные материалы для фармацевтических лабораторий',
    'Materials, reagents and equipment for pharmaceutical laboratories':
        'Reference standards, reagents and consumables for pharmaceutical laboratories',
    'Стандартные образцы, реактивы, хроматография и оборудование ведущих производителей':
        'Стандартные образцы, реактивы и хроматография ведущих производителей',
    'Reference standards, reagents, chromatography supplies and equipment from leading manufacturers':
        'Reference standards, reagents and chromatography supplies from leading manufacturers',
    'Шприцевые фильтры PTFE, Nylon, PVDF, PES и RC с порами 0,22 и 0,45 мкм, виалы и крышки для автосамплера.':
        'Шприцевые фильтры PTFE, Nylon, PVDF, PES и RC с порами 0,22 и 0,45 мкм.',
    'Тест-штаммы ATCC для фармакопейных микробиологических испытаний, лабораторная посуда и фармакопеи. '
    'Перевозка штаммов в нужном температурном режиме.':
        'Тест-штаммы ATCC для фармакопейных микробиологических испытаний и фармакопеи. '
        'Перевозка штаммов в нужном температурном режиме.',
    'Тест-штаммы ATCC, посуда и фармакопеи для микробиологических испытаний.':
        'Тест-штаммы ATCC и фармакопеи для микробиологических испытаний.',
    'Для колонок и оборудования: сертификат производителя и руководство по эксплуатации.':
        'Для колонок: сертификат производителя и руководство по эксплуатации.',
    'For columns and equipment: manufacturer certificate and user manual.':
        'For columns: manufacturer certificate and user manual.',
}
# Phrases inside longer texts.
PHRASES = (
    (', а также посуда и фармакопеи', ', а также фармакопеи'),
    ('расходные материалы для ВЭЖХ и оборудование от', 'расходные материалы для ВЭЖХ от'),
    ('HPLC consumables and equipment from', 'HPLC consumables from'),
    ('стандартные образцы, реактивы и оборудование:', 'стандартные образцы и реактивы:'),
    ('reference standards, reagents and equipment:', 'reference standards and reagents:'),
)


def _removed_href(value: Any) -> bool:
    return isinstance(value, str) and any(f'/catalog/{path}/' in value for path in REMOVED_CATEGORIES)


def clean(node: Any) -> Any:
    """The content without links to the removed categories, blocks scoped only to them and texts offering them."""
    if isinstance(node, dict):
        result = {key: clean(value) for key, value in node.items()}
        if isinstance(result.get('scope'), list):
            result['scope'] = [path for path in result['scope'] if path not in REMOVED_CATEGORIES]
        return result
    if isinstance(node, list):
        items = []
        for item in node:
            if isinstance(item, dict) and _removed_href(item.get('href')):
                continue
            if isinstance(item, dict) and isinstance(item.get('scope'), list) and item['scope'] and all(
                    path in REMOVED_CATEGORIES for path in item['scope']):
                continue
            items.append(clean(item))
        return items
    if isinstance(node, str):
        text = TEXTS.get(node, node)
        for old, new in PHRASES:
            text = text.replace(old, new)
        return text
    return node


EXCLUDED_FILE = Path(__file__).resolve().parents[2] / 'seed' / 'excluded-assortment.csv.gz'


@lru_cache(maxsize=1)
def excluded_assortment() -> frozenset[tuple[str, str]]:
    """(brand key, compact catalog number) of the assortment rows that are not sold: equipment and furniture,
    glassware and consumables except filters, as the business marked them in the catalog of 27.10.2026."""
    if not EXCLUDED_FILE.exists():
        return frozenset()
    with gzip.open(EXCLUDED_FILE, 'rt', encoding='utf-8', newline='') as handle:
        rows = csv.reader(handle)
        next(rows, None)
        return frozenset((brand, number) for brand, number, *_ in rows)


def not_sold(brand_key_value: str, compact_number: str, name: str) -> bool:
    return (brand_key_value, compact_number) in excluded_assortment() or bool(NOT_SOLD.search(name or ''))
