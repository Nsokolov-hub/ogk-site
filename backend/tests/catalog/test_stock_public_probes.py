"""Sources that currently publish price-only catalogues are checked through real linked product scopes."""

import json

import httpx

from app.catalog.stock_sources.additional import algimed_page, algimed_parse
from app.catalog.stock_sources.laverna import page as laverna_page
from app.catalog.stock_sources.probes import hplc_page, lenreactiv_page, neva_page, structured_stock


def client(content):
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=content)))


def test_algimed_discovers_other_published_stock_list_and_three_column_balances():
    content = '<h1>Складские остатки</h1><p>Актуализация: 29 октября 2026 г.</p>' \
        '<table><tr><th>Номенклатура</th><th>Упаковка</th><th>Количество</th></tr>' \
        '<tr><td colspan="3">Thermo Fisher Scientific</td></tr>' \
        '<tr><td>Реагент, 100 мг, Acros Organics, 12345</td><td>уп</td><td>2</td></tr>' \
        '<tr><td>Неопределённый реагент</td><td>уп</td><td>1</td></tr>' \
        '<tr><td>Неизвестный остаток, Acros Organics, 54321</td><td>уп</td><td>_</td></tr></table>' \
        '<a href="#site-navigation">Навигация</a><a href="#content">Содержимое</a>' \
        '<a href="/news/algimed-stocks-of-consumables-and-reagents/#content">Складские остатки</a>' \
        '<a href="https://foreign.example/news/algimed-stocks-of-bad/">Внешний</a>'
    with client(content) as http:
        result = algimed_page(http, {'s': 'algimed'}, lambda name: True)
    assert len(result.offers) == 2
    first, review = result.offers
    assert first.brand_name == 'Acros Organics' and first.catalog_number == '12345' and first.quantity == 2
    assert not first.review_only and first.stock_updated_at is not None
    assert first.stock_updated_at.year == 2026
    assert review.review_only and review.catalog_number == ''
    assert result.tasks == [{'s': 'algimed', 'url':
        'https://algimed.ru/news/algimed-stocks-of-consumables-and-reagents/', 'page': 1}]
    sibling = algimed_parse(content, result.tasks[0]['url'])
    assert sibling.offers[0].url == result.tasks[0]['url']
    assert sibling.offers[0].external_id != first.external_id


def test_hplc_checks_actual_linked_categories_then_products_without_sort_or_spam_urls():
    root = '<a href="index.php?categoryID=351">Колонки</a>' \
        '<a href="index.php?categoryID=431">Стандарты</a><a href="https://spam.example/">Спам</a>'
    with client(root) as http:
        result = hplc_page(http, {'s': 'hplc', 'url': 'https://www.shop.hplc.ru/'}, lambda name: True)
    assert len(result.tasks) == 2 and not result.offers and result.incomplete
    category = '<a href="index.php?productID=6694">Acclaim</a>' \
        '<a href="index.php?categoryID=351&offset=20">2</a>' \
        '<a href="index.php?productID=6694&add=1">Купить</a>'
    with client(category) as http:
        detail = hplc_page(http, result.tasks[0], lambda name: True)
    assert len(detail.tasks) == 1
    assert detail.tasks[0]['url'] == 'https://www.shop.hplc.ru/index.php?productID=6694'
    with client('<h1>Acclaim</h1><p>Цена: 75000 руб. Каталожный номер: 76186</p>') as http:
        empty = hplc_page(http, detail.tasks[0], lambda name: True)
    assert not empty.tasks and not empty.offers and empty.incomplete


def test_neva_checks_catalogue_sections_rows_then_item_details_and_never_uses_prices_as_stock():
    domain = 'https://www.nevareaktiv.ru'
    with client('<a href="/catalog/analiticheskie-standarty">Стандарты</a>') as http:
        root = neva_page(http, {'s': 'nevareaktiv', 'url': domain + '/'}, lambda name: True)
    with client('<a href="/catalog/chistye-veschestva-dlya-hromatografii/items">Чистые вещества</a>') as http:
        section = neva_page(http, root.tasks[0], lambda name: True)
    with client('<a href="/catalog/chistye-veschestva-dlya-hromatografii/items/demo">Реагент</a>'
                '<a href="/catalog/chistye-veschestva-dlya-hromatografii/items?page=2">2</a>') as http:
        items = neva_page(http, section.tasks[0], lambda name: True)
    assert len(items.tasks) == 1
    with client('<h1>Реагент</h1><p>Цена 100 руб. Предложение действительно сегодня.</p>') as http:
        detail = neva_page(http, items.tasks[0], lambda name: True)
    assert not detail.offers and not detail.tasks and detail.incomplete


def test_laverna_checks_linked_detail_and_other_reagent_categories_without_disallowed_pagination():
    content = '<h1>Стандарты</h1><a href="/catalog/385/28792/">Соталол</a>' \
        '<a href="/catalog/454/">Реагенты</a><a href="/catalog/385/?PAGEN_1=2">2</a>'
    with client(content) as http:
        result = laverna_page(http, {'s': 'laverna', 'url': 'https://laverna-xxi.ru/catalog/385/'}, lambda name: True)
    assert len(result.tasks) == 2 and result.incomplete
    detail = next(task for task in result.tasks if task['probe_depth'] == 2)
    with client('<h1>Соталол</h1><p>Артикул: PA 19 0170021. Запросить стоимость</p>') as http:
        empty = laverna_page(http, detail, lambda name: True)
    assert not empty.offers and not empty.tasks


def test_structured_stock_requires_exact_product_scope_and_explicit_offer_marker_and_stays_review_only():
    def document(product, title='Реагент'):
        return '<h1>' + title + '</h1><script type="application/ld+json">' + json.dumps(product) + '</script>'
    product = {'@type': 'Product', 'name': 'Реагент', 'mpn': 'A-1', 'brand': {'name': 'USP'},
               'offers': {'@type': 'Offer', 'availability': 'https://schema.org/InStock'}}
    url = 'https://www.nevareaktiv.ru/catalog/demo/items/demo'
    positive = structured_stock(document(product), url)
    assert len(positive) == 1 and positive[0].review_only
    assert not structured_stock(document({**product, 'url': '/catalog/other/items/demo'}), url)
    assert not structured_stock(document(product, 'Другой товар'), url)
    assert not structured_stock(document({**product, 'offers': {'@type': 'Offer', 'price': '100'}}), url)
    assert not structured_stock(document({**product, 'offers': {'@type': 'Offer',
                                'availability': 'https://schema.org/OutOfStock'}}), url)


def test_lenreactiv_retries_public_shop_and_checks_only_linked_public_shop_pages():
    with client('<a href="/shop/reagents/">Реагенты</a><a href="/shop/?add-to-cart=3">Купить</a>'
                '<a href="/shop/cart/">Корзина</a>') as http:
        root = lenreactiv_page(http, {'s': 'lenreactiv', 'url': 'https://lenreactiv.ru/shop/'}, lambda name: True)
    assert len(root.tasks) == 1 and not root.offers
    assert root.tasks[0]['url'] == 'https://lenreactiv.ru/shop/reagents/'
