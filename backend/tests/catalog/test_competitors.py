"""Stock of suppliers (app.catalog.competitors): Химмед's and Скайклад's warehouse lists make our products «В наличии».

The answers are in the shape the two sites gave on 09.11.2026: Химмед — the page /products/storage with its list of
manufacturers and JSON of POST /products/load (twenty per page, at most ten pages, «perPage» is the page number);
Скайклад — Bitrix cards of /catalog/ with «Доступно: N шт.» and the pager ?PAGEN_1=N.
"""

import html
import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select

from app.catalog import competitors
from app.catalog.models import Brand, BrandAlias, CompetitorOffer, Packaging, Product
from app.catalog.normalize import brand_key, compact
from app.catalog.search.documents import Context, build
from app.catalog.search.query import preview
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.core.db import utcnow

MAKERS = {'E': [['EDQM']], 'S': [['Sigma-Aldrich']], 'A': [['Agilent Technologies', 'Aladdin Scientific']],
          'L': [['Larodan']]}


def storage_page() -> str:
    letters = html.escape(json.dumps(MAKERS, ensure_ascii=True), quote=False).replace("'", '&#039;')
    return (f"<html><body><main><div id=\"storage\" data-type=\"storage\" "
            f"data-letters-and-manufactors='{letters}'></div></main></body></html>")


def chimmed_row(i: int, number: str, maker: str, pack: str = '100 мг', storage: bool = True) -> dict:
    return {'id': 7900000 + i, 'name': f'Позиция {i}', 'art_number': number, 'cas': '28721-07-5', 'packing': pack,
            'price': '14 794,82 ₽', 'product_type': 'Товар со склада' if storage else 'Реактивы & Стандарты',
            'manufactorName': maker, 'sub_type': 'Склад: реактивы', 'storage_product': storage,
            'url': f'pozitsiya-{i}'}


def skygen_card(i: int, number: str, maker: str, left: int) -> str:
    return f'''
    <div class="product-item-container product-item-container-min mb1">
        <div class="product-item" id="bx_3255098535_{190000 + i}">
            <a href="/catalog/item_{i}/" class="product-item-img mb3 d-block"><img src="/x.png"></a>
            <a href="/catalog/item_{i}/" class="product-item-title mb3 d-block">Стандарт {i} &amp; Co</a>
            <div class="article">{number}</div>
            <div class="d-block price-block"><div class="product-item-price-current d-inline-block">
                25 798,28 руб.  <div class="product-item-price-old d-inline-block">36 854,68 руб.</div></div></div>
            <div style="font-size: 14px; margin-top: 0.5rem;">
                Производитель: {maker}                </div>
            <div style="font-size: 14px; margin-top: 0.5rem;">Доступно: {left}
            шт.            </div>
            <form action="/catalog/item_{i}/" method="post"><input type="hidden" name="id" value="{190000 + i}">
            </form>
        </div>
    </div>'''


class FakeSites:
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.refuse: dict[str, int] = {}
        self.edqm = [chimmed_row(1, 'Y0001897', 'EDQM'), chimmed_row(2, 'Y0000881', 'EDQM'),
                     chimmed_row(3, 'B1220000', 'EDQM', storage=False)]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        assert request.headers['User-Agent'] == settings.competitor_user_agent
        if request.url.host in self.refuse:
            return httpx.Response(self.refuse[request.url.host], text='<html>Доступ ограничен</html>')
        if request.url.host == 'chimmed-new.ru':
            return self.chimmed(request)
        assert request.url.host == 'klad.skygen.com'
        assert request.url.path == '/catalog/', 'only the catalogue allowed by robots.txt'
        page = int(request.url.params.get('PAGEN_1', '1'))
        cards = {1: [skygen_card(1, 'sc-300953', 'Santa Cruz', 2), skygen_card(2, 'GKSB-312', 'Agilent', 2)],
                 2: [skygen_card(3, '5190-9015', 'Agilent', 0), skygen_card(4, 'ZZ-1', 'Неизвестный завод', 5),
                     skygen_card(5, '186003116', 'Waters Corporation', 3)]}[page]
        pager = '<a href="/catalog/?PAGEN_1=2">2</a>'
        return httpx.Response(200, text=f'<html><body>{"".join(cards)}{pager}</body></html>')

    def chimmed(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == '/products/storage':
            return httpx.Response(200, text=storage_page())
        assert request.url.path == '/products/load' and request.method == 'POST'
        body = json.loads(request.content)
        assert body['type'] == 'storage' and body['filterStorage'] is True
        maker, letter, page = body['filterManufactor'], body['letter'], body['pagination']['perPage']
        if maker == 'EDQM':
            rows = self.edqm if page == 1 else []
            return httpx.Response(200, json={'products': rows, 'totalPages': 1, 'currentPage': page,
                                             'filters': {'firstLettersProducts': ['О', 'И']}})
        if maker == 'Sigma-Aldrich':
            # Ten pages: the cap — the brand is asked letter by letter.
            if not letter:
                return httpx.Response(200, json={'products': [chimmed_row(10, '413283-100G', maker, '100 г')],
                                                 'totalPages': 10, 'currentPage': page,
                                                 'filters': {'firstLettersProducts': ['1', 'T']}})
            rows = {('1', 1): [chimmed_row(11, '413283-100G', maker, '100 г')],
                    ('T', 1): [chimmed_row(12, 'T5648-1G', maker, '1 г')],
                    ('T', 2): [chimmed_row(13, 'T5648-5G', maker, '5 г')]}.get((letter, page), [])
            return httpx.Response(200, json={'products': rows, 'totalPages': 2 if letter == 'T' else 1,
                                             'currentPage': page, 'filters': {'firstLettersProducts': [letter]}})
        if maker == 'Agilent Technologies':
            return httpx.Response(200, json={'products': {'list': [chimmed_row(20, 'GKSB-312', maker, '1 шт')]},
                                             'totalPages': 1, 'currentPage': page, 'filters': {}})
        raise AssertionError(f'a manufacturer we do not carry was asked: {maker}')


@pytest.fixture
def sites(monkeypatch) -> FakeSites:
    fake = FakeSites()
    monkeypatch.setattr(competitors, 'http_client', lambda: httpx.Client(
        transport=httpx.MockTransport(fake.handle), headers={'User-Agent': settings.competitor_user_agent}))
    monkeypatch.setattr(competitors, 'pause', lambda seconds: None)
    monkeypatch.setattr(settings, 'competitor_stock_enabled', True)
    return fake


def product(db, brand: Brand, number: str, packs: tuple[str, ...] = ()) -> Product:
    row = Product(brand_id=brand.id, catalog_number=number, catalog_number_norm=compact(number),
                  slug=f'{brand.slug}-{compact(number)}', name_en=f'{brand.name} {number}', status='published')
    db.add(row)
    db.flush()
    for i, pack_number in enumerate(packs):
        db.add(Packaging(product_id=row.id, position=i, key=f'p{i}', label_ru='1 г', label_en='1 g',
                         catalog_number=pack_number, catalog_number_norm=compact(pack_number)))
    db.flush()
    return row


@pytest.fixture
def catalog(sessions):
    with sessions.begin() as db:
        brands = {slug: Brand(slug=slug, name=name) for slug, name in
                  (('edqm', 'EDQM'), ('sigma-aldrich', 'Sigma-Aldrich'), ('agilent', 'Agilent'),
                   ('waters', 'Waters'))}
        db.add_all(brands.values())
        db.flush()
        db.add(BrandAlias(brand_id=brands['waters'].id, name='Waters Corporation',
                          normalized=brand_key('Waters Corporation')))
        ids = {
            'oxcarbazepine': product(db, brands['edqm'], 'Y0001897').id,
            'ibuprofen': product(db, brands['edqm'], 'Y0000881').id,
            'edqm-not-in-stock': product(db, brands['edqm'], 'B1220000').id,
            'sigma-pack': product(db, brands['sigma-aldrich'], '413283', packs=('413283-100G',)).id,
            # Their number carries the packaging, ours does not: «T5648-1G» → «T5648».
            'sigma-base': product(db, brands['sigma-aldrich'], 'T5648').id,
            'agilent': product(db, brands['agilent'], 'GKSB-312').id,
            'agilent-sold-out': product(db, brands['agilent'], '5190-9015').id,
            'waters': product(db, brands['waters'], '186003116').id,
        }
        db.execute(Product.__table__.update().values(needs_index=False))
    return ids


def flags(sessions) -> dict[str, bool]:
    with sessions() as db:
        return {p.id: p.supplier_stock for p in db.scalars(select(Product))}


def test_a_check_marks_what_the_suppliers_keep_in_stock(sessions, sites, catalog):
    result = competitors.run_all(sessions)
    assert result and result['finishedAt']
    stock = flags(sessions)
    assert {name for name, pid in catalog.items() if stock[pid]} == {
        'oxcarbazepine', 'ibuprofen', 'sigma-pack', 'sigma-base', 'agilent', 'waters'}

    chimmed, skygen = result['sources']['chimmed'], result['sources']['skygen']
    assert chimmed['complete'] and chimmed['refused'] is None and chimmed['errors'] == 0
    # EDQM (1 page), Sigma: the capped first page, then letters «1» and «T» (two pages), Agilent; Larodan and
    # Aladdin are not our brands and are never asked.
    assert chimmed['pages'] == 1 + 1 + 1 + 1 + 2 + 1
    makers = [json.loads(c.content)['filterManufactor'] for c in sites.calls if c.url.path == '/products/load']
    assert set(makers) == {'EDQM', 'Sigma-Aldrich', 'Agilent Technologies'}
    assert skygen['complete'] and skygen['pages'] == 2 and skygen['matched'] == 2

    with sessions() as db:
        offers = {(o.source, o.catalog_number): o for o in db.scalars(select(CompetitorOffer))}
        # Not a warehouse position, sold out, or a brand we do not carry: not kept.
        assert ('chimmed', 'B1220000') not in offers and ('skygen', '5190-9015') not in offers
        assert ('skygen', 'ZZ-1') not in offers and ('skygen', 'sc-300953') not in offers
        pack = offers[('chimmed', '413283-100G')]
        assert pack.product_id == catalog['sigma-pack'] and pack.packaging_id is not None
        assert offers[('chimmed', 'T5648-5G')].product_id == catalog['sigma-base']
        sky = offers[('skygen', 'GKSB-312')]
        assert sky.quantity == 2 and sky.price == '25 798,28 руб.' and sky.name == 'Стандарт 2 & Co'
        assert sky.url == 'https://klad.skygen.com/catalog/item_2/'
        assert offers[('chimmed', 'Y0001897')].url == 'https://chimmed-new.ru/products/pozitsiya-1-id=7900001'
        # The worker indexes the changed cards again.
        changed = db.scalar(select(func.count()).select_from(Product).where(Product.needs_index))
        assert changed == 6
        # The storefront's preview says «В наличии»; our own availability field stays as the import set it.
        ox = db.get(Product, catalog['oxcarbazepine'])
        assert ox.availability == 'on_order'
        docs, _ = build(db, [ox], Context(db, False))
        assert docs[0]['availability'] == 'in_stock' and docs[0]['stock'] == 'supplier'
        assert preview(docs[0], 'ru')['availability'] == 'in_stock'
        assert get_setting(db, 'competitor_run') is None
    # Not due again before every_days.
    assert competitors.turn(sessions) is None


def test_a_position_gone_from_a_checked_site_is_no_longer_in_stock(sessions, sites, catalog):
    competitors.run_all(sessions)
    sites.edqm = [chimmed_row(1, 'Y0001897', 'EDQM')]  # ibuprofen sold out at Химмед
    with sessions.begin() as db:
        set_setting(db, 'competitor_results', {**get_setting(db, 'competitor_results'), 'finishedAt': None})
    result = competitors.run_all(sessions)
    assert result['left'] == 1
    stock = flags(sessions)
    assert stock[catalog['oxcarbazepine']] and not stock[catalog['ibuprofen']]


def test_a_refusing_site_is_left_alone_and_its_stock_expires_after_keep_days(sessions, sites, catalog):
    competitors.run_all(sessions)
    sites.calls.clear()
    sites.refuse = {'klad.skygen.com': 403}
    with sessions.begin() as db:
        set_setting(db, 'competitor_results', {**get_setting(db, 'competitor_results'), 'finishedAt': None})
    result = competitors.run_all(sessions)
    skygen = result['sources']['skygen']
    assert skygen['refused'] == '403' and not skygen['complete']
    # One refused request, then the site is not asked again in this check — no retries around a refusal.
    assert len([c for c in sites.calls if c.url.host == 'klad.skygen.com']) == 1
    # Its offers from the last check still count…
    assert flags(sessions)[catalog['waters']]
    # …until they are older than keep_days.
    with sessions.begin() as db:
        db.execute(CompetitorOffer.__table__.update().where(CompetitorOffer.source == 'skygen')
                   .values(seen_at=utcnow() - timedelta(days=11)))
        competitors.settle(db, utcnow(), [], utcnow())
    stock = flags(sessions)
    assert not stock[catalog['waters']] and stock[catalog['oxcarbazepine']]


def test_a_captcha_page_counts_as_a_refusal(sessions, sites, catalog, monkeypatch):
    real = sites.handle

    def handle(request):
        if request.url.host == 'chimmed-new.ru':
            return httpx.Response(200, text='<html><form action="/check"><div class="smartcaptcha"></div></form>')
        return real(request)

    sites.handle = handle  # type: ignore[method-assign]
    result = competitors.run_all(sessions)
    assert result['sources']['chimmed']['refused'] == 'captcha'
    assert result['sources']['skygen']['complete']


def test_the_check_goes_in_short_turns_and_continues_after_a_restart(sessions, sites, catalog, monkeypatch):
    clock = {'now': 0.0}
    monkeypatch.setattr(competitors.time, 'monotonic', lambda: clock['now'])

    def slow(seconds):
        clock['now'] += 10  # every pause «takes» ten seconds: three pages per turn of 20 s

    monkeypatch.setattr(competitors, 'pause', slow)
    turns = 0
    while True:
        step = competitors.turn(sessions, seconds=20)
        turns += 1
        if step is None or 'finishedAt' in step:
            break
        with sessions() as db:  # the queue is in the database: a new worker would continue it
            assert get_setting(db, 'competitor_run')['queue']
    assert turns >= 3 and step and step['sources']['chimmed']['complete']
    assert len(sites.calls) == 9  # nine pages in all, three per turn
    assert flags(sessions)[catalog['sigma-base']]


def test_nothing_is_checked_outside_production_unless_turned_on(sessions, monkeypatch):
    monkeypatch.setattr(settings, 'competitor_stock_enabled', None)
    monkeypatch.setattr(settings, 'environment', 'staging')
    with sessions() as db:
        assert not competitors.due(db)
    monkeypatch.setattr(settings, 'environment', 'production')
    with sessions() as db:
        assert competitors.due(db)


def test_brand_spellings_of_the_suppliers(sessions, catalog):
    with sessions.begin() as db:
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'),
                                             'brand_aliases': {'Supelco': 'sigma-aldrich'}})
        brands = competitors.Brands(db)
        slug = {b.id: b.slug for b in db.scalars(select(Brand))}
    assert slug[brands.find('Agilent Technologies')] == 'agilent'
    assert slug[brands.find('Waters Corporation')] == 'waters'
    assert slug[brands.find('Supelco')] == 'sigma-aldrich'
    assert brands.find('Aladdin Scientific') is None and brands.find('USP') is None

