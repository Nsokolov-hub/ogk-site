"""Semantic fixtures from the visible public pages inspected on 20 November 2026.

These examples verify header/row/card boundaries. They are intentionally not presented as captured raw HTML:
the research tool exposes rendered semantics, and deployments must surface parser drift as incomplete.
"""

import httpx
import pytest

from app.catalog.stock_sources import dia_m, labteh, laverna, vilax
from app.catalog.stock_sources.base import ParseChanged, Refused
from app.catalog.stock_sources.html import Document, links


def test_diam_distinguishes_variants_and_uses_the_manufacturer_not_analogue():
    page = '''<h1>Реактив Фишера (аналог Sigma, Merck) <a href="/vendors/russia/">Россия</a></h1>
    <table><tr><th>Артикул</th><th></th><th></th><th>Цена, руб.</th><th>Наличие на складе</th></tr>
    <tr><td>800.1000</td><td></td><td>1 л</td><td>8 619</td><td>Под заказ</td></tr></table>
    <table><tr><th>Артикул</th><th></th><th></th><th>Цена, руб.</th><th>Наличие на складе</th></tr>
    <tr><td>800.2500</td><td></td><td>2,5 л</td><td>17 921</td><td>В наличии</td></tr></table>
    <h2>Описание</h2><aside>С этим товаром покупают <a href="/catalog/reactive/another/">Sigma 123</a>
    <table><tr><th>Артикул</th><th>Наличие на складе</th></tr>
    <tr><td>999999</td><td>В наличии</td></tr></table></aside>'''
    out = dia_m.parse(page, f'{dia_m.START}reaktiv-fishera-marka-akva-m-solvent/')
    assert [(offer.brand_name, offer.catalog_number, offer.pack) for offer in out.offers] == [
        ('Россия', '800.2500', '2,5 л')]
    assert out.offers[0].quantity is None and out.offers[0].stock_updated_at is None
    assert not out.tasks and not out.incomplete


def test_diam_preserves_cas_and_never_turns_transit_or_prose_into_stock():
    page = '''<h1>Акриламид <a href="/vendor/diam/">Диаэм</a></h1>
    <p>Большая часть реактивов на складе.</p><table><tr><td>CAS-No.</td><td>79-06-1</td></tr></table>
    <table><tr><td>Артикул</td><td></td><td>Фасовка</td><td>Цена, руб.</td><td>Наличие на складе</td></tr>
    <tr><td>3625</td><td></td><td>50 г</td><td>1005</td><td>В наличии</td></tr>
    <tr><td>3626</td><td></td><td>1 кг</td><td>3000</td><td>В транзите</td></tr></table>
    <aside><table><tr><td>CAS-No.</td><td>50-00-0</td></tr></table></aside>'''
    out = dia_m.parse(page, f'{dia_m.START}akrilamid-ultrachistyy/')
    assert len(out.offers) == 1 and out.offers[0].cas == '79-06-1'
    assert out.offers[0].catalog_number == '3625'


def test_diam_discovers_only_visible_public_catalogue_links():
    page = '''<h1>Химические реактивы на складе</h1>
    <a href="/catalog/reactive/buffers/">Буферы</a>
    <a href="/catalog/reactive/buffers/?getItems=1">Скрытая загрузка</a>
    <a href="/search/?q=water">Поиск</a><a href="https://other.test/catalog/reactive/">Другой сайт</a>'''
    out = dia_m.parse(page, dia_m.START)
    assert out.tasks == [{'s': 'diam', 'url': f'{dia_m.START}buffers/', 'page': 1}]
    assert not out.offers
    with pytest.raises(ParseChanged):
        dia_m.parse('<h1>Проверка страницы</h1>', dia_m.START)


def test_diam_marks_an_unknown_stock_column_incomplete():
    page = '''<h1>Test <a>Unknown maker</a></h1><table>
    <tr><th>Артикул</th><th>Наличие на складе</th></tr>
    <tr><td>ABC123</td><td>Уточните у менеджера</td></tr></table>'''
    out = dia_m.parse(page, f'{dia_m.START}item/')
    assert out.incomplete == 'stock_marker_changed' and not out.offers


def test_diam_requires_a_declared_manufacturer_for_a_positive_product_row():
    page = '''<h1>Название без производителя</h1><table>
    <tr><th>Артикул</th><th>Наличие на складе</th></tr>
    <tr><td>ABC123</td><td>В наличии</td></tr></table>'''
    out = dia_m.parse(page, f'{dia_m.START}item/')
    assert out.incomplete == 'manufacturer_brand_missing' and not out.offers


def test_labteh_uses_delivery_cell_not_price_and_does_not_use_internal_sku():
    page = '''<h1>Химические реактивы</h1><table>
    <tr><th>Наименование</th><th>Цена без НДС</th><th>НДС</th><th>Срок поставки</th></tr>
    <tr><td><a href="/catalog/khimicheskie-reaktivy/sigma/a/">L-Цистеин, 97%, 25 г,
    Sigma-Aldrich 168149, CAS 52-90-4, 2-03783</a></td><td>8713</td><td>22%</td><td>10-12 нед.</td></tr>
    <tr><td><a href="/catalog/khimicheskie-reaktivy/sigma/b/?sphrase_id=1">Ментол, 1 г,
    Sigma 63660, CAS 2216-51-5, 2-01945</a></td><td>8991 ₽</td><td>22%</td><td>В наличии</td></tr></table>
    <a href="?PAGEN_1=2">2</a><a href="/personal/">Войти</a>'''
    out = labteh.parse(page, labteh.START)
    assert len(out.offers) == 1
    offer = out.offers[0]
    assert (offer.brand_name, offer.catalog_number, offer.pack, offer.cas) == ('Sigma', '63660', '1 г', '2216-51-5')
    assert offer.url.endswith('/sigma/b/') and 'sphrase_id' not in offer.url
    assert out.tasks == [{'s': 'labteh', 'url': f'{labteh.START}?PAGEN_1=2', 'page': 2}]
    assert not out.incomplete


def test_labteh_reports_a_changed_layout_or_unverifiable_stock_identity():
    with pytest.raises(ParseChanged):
        labteh.parse('<h1>Каталог</h1><p>Скоро новые товары</p>', labteh.START)
    page = '''<h1>Каталог</h1><table><tr><th>Наименование</th><th>Срок поставки</th></tr>
    <tr><td><a href="/catalog/khimicheskie-reaktivy/item/">Реактив, 2-12345</a></td>
    <td>В наличии</td></tr></table>'''
    out = labteh.parse(page, labteh.START)
    assert not out.offers and out.incomplete == 'manufacturer_identity_missing'


def test_vilax_uses_only_stock_within_the_same_product_card():
    url = f'{vilax.ORIGIN}/catalog/oborudovanie_i_materialy/welch/'
    page = '''<h1>Welch</h1><p>Мы поставляем материалы со склада.</p>
    <div><a href="/catalog/oborudovanie_i_materialy/welch/kolonki_vezhkh/xtimate/2496/">
    Welch 00101-27019 Колонка Xtimate C18</a><div>Есть в наличии: 3</div><span>62 049.60 ₽/шт</span></div>
    <div><a href="/catalog/oborudovanie_i_materialy/welch/kolonki_vezhkh/xtimate/2497/">
    Welch 00101-21043 Колонка Xtimate C18</a><div>Нет в наличии</div><span>71 539 ₽/шт</span></div>
    <a href="?PAGEN_1=2">2</a>'''
    out = vilax.parse(page, url)
    assert [(offer.brand_name, offer.catalog_number, offer.quantity) for offer in out.offers] == [
        ('Welch', '00101-27019', 3)]
    assert out.offers[0].price == '62 049.60 ₽'
    assert out.tasks == [{'s': 'vilax', 'url': f'{url}?PAGEN_1=2', 'page': 2}]


def test_vilax_empty_original_category_follows_observed_welch_link_as_incomplete():
    page = '''<h1>Хроматографическая колонка</h1><p>Не нашли товары в разделе?</p>
    <p>Некоторые позиции уже могут быть в наличии — уточните у менеджера.</p>
    <a href="/catalog/oborudovanie_i_materialy/welch/">Welch</a>'''
    out = vilax.parse(page, vilax.START)
    assert out.incomplete and not out.offers and len(out.tasks) == 1
    with pytest.raises(ParseChanged):
        vilax.parse('<h1>Добро пожаловать</h1>', vilax.START)


def test_laverna_request_price_and_generic_warehouse_claim_are_not_stock():
    page = '''<h1>Пальмитиновая кислота</h1><div>Артикул: PA 27 01480</div>
    <p>Pharmaffiliates имеет на складе более 10000 стандартов.</p><button>Запросить стоимость</button>
    <dl><dt>CAS номер</dt><dd>57-10-3</dd></dl>'''
    out = laverna.parse(page)
    assert out.incomplete == 'no_stock_evidence' and not out.offers


def test_public_links_reject_hidden_queries_private_paths_and_other_origins():
    root = Document('''<a href="?PAGEN_1=2">2</a><a href="?q=123">search</a>
    <a href="/catalog/reactive/?action=buy">buy</a><a href="//other.test/catalog/reactive/">other</a>
    <a href="/catalog/reactive/ok/#details">okay</a>''').root
    assert links(root, dia_m.START, dia_m.PREFIXES) == [f'{dia_m.START}?PAGEN_1=2', f'{dia_m.START}ok/']


@pytest.mark.parametrize('module', [dia_m, labteh, laverna, vilax])
def test_a_block_or_captcha_never_produces_offers(module):
    for status, body in [(403, 'Forbidden'), (429, 'Rate limit'), (200, '<form><div class="smartcaptcha"></div></form>')]:
        calls: list[httpx.Request] = []

        def handle(request, calls=calls, status=status, body=body):
            calls.append(request)
            return httpx.Response(status, text=body)

        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(Refused):
                module.page(client, {'url': module.START}, lambda _: True)
        assert len(calls) == 1
