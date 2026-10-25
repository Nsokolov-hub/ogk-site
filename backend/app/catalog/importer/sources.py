"""Sources of price lists with their column templates (IMP-01, IMP-02).

A template maps catalog fields to column titles. It is saved on the source in the database the first time, so
the admin panel's wizard can show and change it later.
"""

from typing import Any

FIELDS = ('brand', 'catalog_number', 'name', 'cas', 'pack', 'availability')
REQUIRED = ('brand', 'catalog_number')

TEMPLATES: dict[str, dict[str, Any]] = {
    # The assortment export of 17.10.2026 (TZ 9.6): 2.4 million rows, 325 manufacturers. Only the list of items
    # is taken: manufacturer, catalog number, CAS and packagings. Prices, stock, sections, characteristics,
    # descriptions and links are not imported; every item is «Под заказ».
    'assortment': {
        'name': 'Выгрузка ассортимента (ТЗ 9.6)',
        'mapping': {'brand': 'Производитель', 'catalog_number': 'Кат. №', 'name': 'Наименование', 'cas': 'CAS',
                    'pack': 'Фасовка'},
        'options': {
            'skip_brands': ['Химмед', 'Chimmed'],
            # Names written in Latin are the manufacturer's catalog names; translated ones are the source's text
            # and stay internal (NFR-09). Without a Latin name the card is named by its substance or number.
            'names': 'latin',
            'availability': 'on_order',
            # The first load meets every manufacturer for the first time: they become brands without a page,
            # each listed once in the journal for review; ordinary price lists send unknown brands to the queue.
            'create_brands': True,
            'group_pack_suffix': True,
            'full_source': True,
        },
    },
    # A supplier's price list with the usual columns; availability «В наличии» marks the real stock.
    'price': {
        'name': 'Прайс поставщика',
        'mapping': {'brand': 'Производитель', 'catalog_number': 'Кат. №', 'name': 'Наименование', 'cas': 'CAS',
                    'pack': 'Фасовка', 'availability': 'Наличие'},
        'options': {'names': 'all', 'availability': 'column', 'create_brands': False, 'group_pack_suffix': True,
                    'full_source': False},
    },
}
