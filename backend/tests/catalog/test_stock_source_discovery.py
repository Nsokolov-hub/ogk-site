"""Regressions for the public catalogue structures inspected on 22 November 2026."""

from app.catalog.stock_sources import dia_m, labteh, vilax
from app.catalog.stock_sources.html import identity


def test_diam_reads_model_stock_in_alphabet_cards_without_fetching_each_detail():
    page = '''<h1>Реактивы: А</h1><p>Большая часть на складе</p>
    <article class="product-card collapse"><a class="product-card__name"
      href="/catalog/reactive/agar/">Агар,</a>
      <div class="product-model" data-value="910780.100 gm" data-manufacturer="CDH, Индия">
        <span class="product-model__article">910780.100 gm</span>
        <div class="product-model__amount">100 г</div>
        <div class="product-model__status product-model__status--available" title="В наличии"></div>
        <div class="product-model__price">4 208 руб.</div>
      </div><div class="product-model" data-value="910780.500 gm" data-manufacturer="CDH, Индия">
        <span class="product-model__article">910780.500 gm</span>
        <div class="product-model__amount">500 г</div>
        <div class="product-model__status" title="В транзите"></div>
      </div><div>CAS 9002-18-0</div></article>
    <article class="product-card"><a class="product-card__link"
      href="/catalog/reactive/another/">См. другой продукт</a></article>
    <a href="/catalog/reactive/letter-29/">Б</a>'''
    result = dia_m.parse(page, dia_m.START + 'letter-28/')
    assert len(result.offers) == 1
    offer = result.offers[0]
    assert (offer.brand_name, offer.catalog_number, offer.pack, offer.cas) == (
        'CDH, Индия', '910780.100 gm', '100 г', '9002-18-0')
    assert offer.quantity is None and not result.incomplete
    assert {task['url'] for task in result.tasks} == {
        dia_m.START + 'another/', dia_m.START + 'letter-29/'}


def test_diam_does_not_inherit_a_neighbouring_cards_identity_or_generic_stock():
    page = '''<h1>Химические реактивы на складе</h1>
    <article class="product-card"><a class="product-card__name" href="/catalog/reactive/a/">A</a>
      <div class="product-model" data-value="other" data-manufacturer="CDH">
        <span class="product-model__article">ABC</span><div class="product-model__amount">100 г</div>
        <div class="product-model__status" title="В наличии"></div></div></article>
    <article class="product-card"><a class="product-card__name" href="/catalog/reactive/b/">B</a>
      <div class="product-model" data-value="DEF" data-manufacturer="Sigma">
        <span class="product-model__article">DEF</span><div class="product-model__amount">1 г</div>
        <div class="product-model__status" title="Под заказ"></div></div></article>'''
    result = dia_m.parse(page, dia_m.START)
    assert not result.offers and result.incomplete == 'catalogue_card_identity_changed'


def test_diam_prioritizes_remaining_detail_links_over_repeated_alphabet_navigation():
    page = '''<h1>А</h1><a href="/catalog/reactive/letter-29/">Б</a>
    <a class="product-card__name" href="/catalog/reactive/agar/">Агар</a>'''
    result = dia_m.parse(page, dia_m.START + 'letter-28/')
    assert [task['url'] for task in result.tasks] == [dia_m.START + 'agar/', dia_m.START + 'letter-29/']


def test_labteh_parent_lists_cover_manufacturer_categories_without_duplicate_crawl():
    page = '''<h1>Химические реактивы</h1><table>
    <tr><th>Наименование</th><th>Срок поставки</th></tr></table>
    <a href="/catalog/khimicheskie-reaktivy/khimreaktivy-sigma-aldrich/">Sigma</a>
    <a href="/catalog/standarty/">Стандарты</a><a href="?PAGEN_1=2">2</a>'''
    result = labteh.parse(page, labteh.START)
    assert [task['url'] for task in result.tasks] == [labteh.START + '?PAGEN_1=2', labteh.ORIGIN + '/catalog/standarty/']


def test_vilax_chemical_reagents_are_discovered_and_bottle_pack_beats_sale_unit():
    url = vilax.ORIGIN + '/catalog/khimicheskie_reaktivy/alpha_chemika/'
    page = '''<h1>Alpha Chemika</h1><div class="catalog_item">
      <div class="item_info"><div class="item_info--top_block"><div class="item-title">
      <a href="/catalog/khimicheskie_reaktivy/alpha_chemika/2673/">Alpha AL1852.0100 Реактив (100г)</a>
      </div><div>Есть в наличии: 2</div></div><div>2 241 ₽ <span>/шт</span></div></div></div>
      <a href="?PAGEN_1=2">2</a>'''
    result = vilax.parse(page, url)
    assert len(result.offers) == 1
    offer = result.offers[0]
    assert (offer.brand_name, offer.catalog_number, offer.pack, offer.quantity, offer.price) == (
        'Alpha', 'AL1852.0100', '100г', 2, '2 241 ₽')
    assert len(result.tasks) == 1 and result.tasks[0]['url'] == url + '?PAGEN_1=2'


def test_vilax_unit_comes_from_same_single_product_scope_only():
    url = vilax.ORIGIN + '/catalog/oborudovanie_i_materialy/welch/'
    page = '''<h1>Welch</h1><div><div><div><a
      href="/catalog/oborudovanie_i_materialy/welch/2496/">Welch 00101-27019 Колонка</a>
      <span>Есть в наличии: 3</span></div><span>62 049.60 ₽ /шт</span></div></div>
      <div><a href="/catalog/oborudovanie_i_materialy/welch/2497/">Welch 00101-21043 Колонка</a>
      <span>Нет в наличии</span><span>100 ₽ /шт</span></div>'''
    result = vilax.parse(page, url)
    assert len(result.offers) == 1
    assert (result.offers[0].pack, result.offers[0].price) == ('1 шт', '62 049.60 ₽')


def test_vilax_a_missing_stock_marker_is_incomplete_instead_of_verified_empty():
    page = '''<h1>Welch</h1><div><a href="/catalog/oborudovanie_i_materialy/welch/2496/">
      Welch 00101-27019 Колонка</a><span>62 049.60 ₽ /шт</span></div>'''
    result = vilax.parse(page, vilax.ORIGIN + vilax.PREFIXES[0])
    assert not result.offers and result.incomplete == 'card_stock_marker_missing'


def test_vilax_does_not_inherit_stock_from_a_neighbour_with_an_unrecognized_title():
    page = '''<h1>Колонки</h1><div><div>
      <a href="/catalog/oborudovanie_i_materialy/welch/2496/">Welch 00101-27019 Колонка</a>
      <span>Цену уточняйте</span></div><div>
      <a href="/catalog/oborudovanie_i_materialy/welch/2497/">Other Scientific ABC123 Другая колонка</a>
      <span>Есть в наличии: 5</span><span>100 ₽ /шт</span></div></div>'''
    result = vilax.parse(page, vilax.ORIGIN + vilax.PREFIXES[0])
    assert not result.offers and result.incomplete == 'card_stock_marker_missing'


def test_diam_table_withdraws_only_explicit_negative_variants_in_the_main_product():
    url = dia_m.START + 'reagent/'
    page = '''<h1>Reagent <a>Merck</a></h1><table>
      <tr><th>Артикул</th><th>Фасовка</th><th>Наличие на складе</th></tr>
      <tr><td>SKU-100G</td><td>100 г</td><td>Под заказ</td></tr>
      <tr><td>SKU-500G</td><td>500 г</td><td>В наличии</td></tr>
      <tr><td>SKU-ZERO</td><td>1 г</td><td>В наличии: 0</td></tr>
      <tr><td>SKU-UNKNOWN</td><td>2 г</td><td>Уточните у менеджера</td></tr>
      </table><h2>Описание</h2><aside><table>
      <tr><th>Артикул</th><th>Фасовка</th><th>Наличие на складе</th></tr>
      <tr><td>NEIGHBOUR</td><td>25 г</td><td>Нет в наличии</td></tr></table></aside>'''
    result = dia_m.parse(page, url)
    assert result.unavailable_ids == [identity(url, 'SKU-100G', '100 г'), identity(url, 'SKU-ZERO', '1 г')]
    assert [offer.catalog_number for offer in result.offers] == ['SKU-500G']
    assert result.incomplete == 'stock_marker_changed'


def test_diam_variant_cards_withdraw_same_url_article_pack_and_do_not_guess_unknown_state():
    url = dia_m.START + 'letter-28/'
    product = dia_m.START + 'reagent/'
    page = '''<h1>А</h1><article class="product-card"><a class="product-card__name"
      href="/catalog/reactive/reagent/">Reagent</a>
      <div class="product-model" data-value="SKU-100G" data-manufacturer="Merck">
        <span class="product-model__article">SKU-100G</span><div class="product-model__amount">100 г</div>
        <div class="product-model__status" title="В транзите"></div></div>
      <div class="product-model" data-value="SKU-500G" data-manufacturer="Merck">
        <span class="product-model__article">SKU-500G</span><div class="product-model__amount">500 г</div>
        <div class="product-model__status" title="В наличии"></div></div>
      <div class="product-model" data-value="SKU-ZERO" data-manufacturer="Merck">
        <span class="product-model__article">SKU-ZERO</span><div class="product-model__amount">1 г</div>
        <div class="product-model__status" title="В наличии: 0"></div></div>
      <div class="product-model" data-value="SKU-UNKNOWN" data-manufacturer="Merck">
        <span class="product-model__article">SKU-UNKNOWN</span><div class="product-model__amount">2 г</div>
        <div class="product-model__status" title="Уточните у менеджера"></div></div>
      <div class="product-model" data-value="WRONG-SKU" data-manufacturer="Merck">
        <span class="product-model__article">NOT-MATCHING</span><div class="product-model__amount">3 г</div>
        <div class="product-model__status" title="Нет в наличии"></div></div></article>'''
    result = dia_m.parse(page, url)
    assert result.unavailable_ids == [identity(product, 'SKU-100G', '100 г'), identity(product, 'SKU-ZERO', '1 г')]
    assert [offer.catalog_number for offer in result.offers] == ['SKU-500G']
    assert result.incomplete and result.tasks
