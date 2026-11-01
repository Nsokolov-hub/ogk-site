"""Sources of price lists with their column templates (IMP-01, IMP-02).

A template maps catalog fields to column titles. It is saved on the source in the database the first time, so
the admin panel's wizard can show and change it later.
"""

from typing import Any

FIELDS = ('brand', 'catalog_number', 'name', 'cas', 'pack', 'availability', 'characteristics', 'direction', 'section',
          'subgroup')
REQUIRED = ('brand', 'catalog_number')
# The export's own products are not imported; the list lives in code so the database never names the source.
SOURCE_BRANDS = ('Химмед', 'Chimmed')
# Options of older saved templates that are no longer used.
OBSOLETE_OPTIONS = ('skip_brands',)

TEMPLATES: dict[str, dict[str, Any]] = {
    # The assortment export of 17.10.2026 (TZ 9.6): 2.4 million rows, 325 manufacturers. Taken: manufacturer,
    # catalog number, CAS, packagings, the manufacturer's Latin name and, from the characteristics, only the gross
    # formula and the molecular weight. Prices, stock, sections, the rest of the characteristics, descriptions,
    # the source's links and ids are never read; every item is «Под заказ».
    'assortment': {
        'name': 'Выгрузка ассортимента (ТЗ 9.6)',
        'mapping': {'brand': 'Производитель', 'catalog_number': 'Кат. №', 'name': 'Наименование', 'cas': 'CAS',
                    'pack': 'Фасовка', 'characteristics': 'Характеристики'},
        'options': {
            'exclude_source_brand': True,
            'chemical_facts': True,
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
    # The same assortment as the business laid it out by direction, category and subgroup («Каталог продукции по
    # категориям», 31.10.2026): one sheet per direction after the contents, the column titles under a title row.
    # Read as the export above; the card's category comes from these three columns (rules.FILE_CATEGORIES), and the
    # directions the business does not sell (equipment, glassware except filters, «Прочие товары») are skipped.
    'catalog': {
        'name': 'Каталог по категориям',
        'mapping': {'brand': 'Производитель', 'catalog_number': 'Кат. №', 'name': 'Наименование', 'cas': 'CAS',
                    'pack': 'Фасовка', 'characteristics': 'Характеристики', 'direction': 'Направление',
                    'section': 'Категория', 'subgroup': 'Подгруппа'},
        'options': {
            'exclude_source_brand': True,
            'chemical_facts': True,
            'names': 'latin',
            'availability': 'on_order',
            'create_brands': True,
            'group_pack_suffix': True,
            'full_source': True,
            'all_sheets': True,
            'file_categories': True,
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
