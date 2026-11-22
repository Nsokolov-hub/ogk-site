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
from sqlalchemy import func, select, update

from app.catalog import competitors
from app.catalog.identity import ALIASES, MASTER_SLUG, REVIEW, SOURCE_URL
from app.catalog.models import Brand, BrandAlias, CompetitorOffer, Packaging, Product
from app.catalog.normalize import brand_key, compact, parse_pack, split_pack_suffix
from app.catalog.search.documents import Context, build
from app.catalog.search.query import preview
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.core.db import as_utc, utcnow

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
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /products/\nAllow: /catalog/\n')
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
        assert maker in {'Aladdin Scientific', 'Larodan'}
        return httpx.Response(200, json={'products': [chimmed_row(30 if maker == 'Larodan' else 31,
                                                                'NEW-1', maker)], 'totalPages': 1})


@pytest.fixture
def sites(monkeypatch, sessions) -> FakeSites:
    fake = FakeSites()
    monkeypatch.setattr(competitors, 'http_client', lambda: httpx.Client(
        transport=httpx.MockTransport(fake.handle), headers={'User-Agent': settings.competitor_user_agent}))
    monkeypatch.setattr(competitors, 'pause', lambda seconds: None)
    monkeypatch.setattr(settings, 'competitor_stock_enabled', True)
    with sessions.begin() as db:
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'),
                                            'sources': ['chimmed', 'skygen']})
    return fake


def product(db, brand: Brand, number: str, packs: tuple[str, ...] = (), default_pack: str = '1 g') -> Product:
    row = Product(brand_id=brand.id, catalog_number=number, catalog_number_norm=compact(number),
                  slug=f'{brand.slug}-{compact(number)}', name_en=f'{brand.name} {number}', status='published')
    db.add(row)
    db.flush()
    for i, pack_number in enumerate(packs):
        _base, size = split_pack_suffix(pack_number, None)
        size = size or parse_pack(default_pack)
        assert size is not None
        db.add(Packaging(product_id=row.id, position=i, key=f'p{i}', label_ru=size.label_ru,
                         label_en=size.label_en, amount=size.amount, unit=size.unit,
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
            'oxcarbazepine': product(db, brands['edqm'], 'Y0001897', packs=('Y0001897',), default_pack='100 mg').id,
            'ibuprofen': product(db, brands['edqm'], 'Y0000881', packs=('Y0000881',), default_pack='100 mg').id,
            'edqm-not-in-stock': product(db, brands['edqm'], 'B1220000', packs=('B1220000',), default_pack='100 mg').id,
            'sigma-pack': product(db, brands['sigma-aldrich'], '413283', packs=('413283-100G',)).id,
            # Product article stays generic; each stocked variant has an explicit manufacturer packaging.
            'sigma-base': product(db, brands['sigma-aldrich'], 'T5648', packs=('T5648-1G', 'T5648-5G')).id,
            'agilent': product(db, brands['agilent'], 'GKSB-312', packs=('GKSB-312',), default_pack='1 pcs').id,
            'agilent-sold-out': product(db, brands['agilent'], '5190-9015', packs=('5190-9015',), default_pack='1 pcs').id,
            'waters': product(db, brands['waters'], '186003116', packs=('186003116',), default_pack='1 pcs').id,
        }
        db.execute(update(Product).values(needs_index=False))
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
    # All manufacturers are checked, including new brands kept privately for manager review.
    assert chimmed['pages'] == 1 + 1 + 1 + 1 + 2 + 1 + 2
    makers = [json.loads(c.content)['filterManufactor'] for c in sites.calls if c.url.path == '/products/load']
    assert set(makers) == {'EDQM', 'Sigma-Aldrich', 'Agilent Technologies', 'Aladdin Scientific', 'Larodan'}
    assert skygen['complete'] and skygen['pages'] == 2 and skygen['matched'] == 2

    with sessions() as db:
        offers = {(o.source, o.catalog_number): o for o in db.scalars(select(CompetitorOffer))}
        # Non-stock/sold-out rows are excluded. New brands are retained for private review.
        assert ('chimmed', 'B1220000') not in offers and ('skygen', '5190-9015') not in offers
        assert offers[('skygen', 'ZZ-1')].product_id is None
        assert offers[('skygen', 'sc-300953')].product_id is None
        assert offers[('chimmed', 'NEW-1')].product_id is None
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
    assert result is not None
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
    assert result is not None
    skygen = result['sources']['skygen']
    assert skygen['refused'] == '403' and not skygen['complete']
    # One refused request, then the site is not asked again in this check — no retries around a refusal.
    assert len([c for c in sites.calls if c.url.host == 'klad.skygen.com']) == 1
    # Its offers from the last check still count…
    assert flags(sessions)[catalog['waters']]
    # …until they are older than keep_days.
    with sessions.begin() as db:
        db.execute(update(CompetitorOffer).where(CompetitorOffer.source == 'skygen')
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
    assert result is not None
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
    assert len([c for c in sites.calls if c.url.path != '/robots.txt']) == 11
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


def test_brand_prefixes_and_ambiguous_aliases_cannot_publish_stock(sessions, catalog):
    with sessions.begin() as db:
        brands = competitors.Brands(db)
        assert brands.find('Agilent unrelated manufacturer') is None
        assert brands.find('Agilent') is not None
        sigma = db.scalar(select(Brand).where(Brand.slug == 'sigma-aldrich'))
        db.add(BrandAlias(brand_id=sigma.id, name='Agilent', normalized=brand_key('Agilent')))
        db.flush()
        assert competitors.Brands(db).find('Agilent') is None


def test_conflicting_cas_or_pack_size_stays_unmatched_for_review(sessions, catalog):
    with sessions.begin() as db:
        sigma = db.get(Product, catalog['sigma-pack'])
        sigma.cas = '50-00-0'
        offers = [
            competitors.Offer('cas-conflict', 'Sigma-Aldrich', '413283-100G', 'Other substance',
                              'https://chimmed-new.ru/products/a', cas='64-17-5', pack='100 g'),
            competitors.Offer('pack-conflict', 'Sigma-Aldrich', '413283-5G', 'Other pack',
                              'https://chimmed-new.ru/products/b', cas='50-00-0', pack='5 g'),
        ]
        kept, matched = competitors.save(db, 'chimmed', offers, competitors.Brands(db), utcnow())
        assert (kept, matched) == (2, 0)
        assert not db.get(Product, catalog['sigma-pack']).supplier_stock
        assert all(o.product_id is None for o in db.scalars(select(CompetitorOffer)))
        assert competitors.status(db)['pendingReview'] == 2


def test_zero_quantity_removes_previous_offer_and_flag(sessions, catalog):
    now = utcnow()
    with sessions.begin() as db:
        offer = competitors.Offer('qty', 'Agilent', 'GKSB-312', 'Product',
                                  'https://klad.skygen.com/catalog/a/', quantity=2)
        brands = competitors.Brands(db)
        competitors.save(db, 'skygen', [offer], brands, now)
        assert db.get(Product, catalog['agilent']).supplier_stock
        offer.quantity = 0
        assert competitors.save(db, 'skygen', [offer], brands, now) == (0, 0)
        assert not db.get(Product, catalog['agilent']).supplier_stock
        assert db.scalar(select(func.count()).select_from(CompetitorOffer)) == 0


def test_positive_recheck_renews_the_search_document_deadline(sessions, catalog):
    with sessions.begin() as db:
        now = utcnow()
        offer = competitors.Offer('renewed', 'Agilent', 'GKSB-312', 'Product',
                                  'https://klad.skygen.com/catalog/a/', quantity=1)
        brands = competitors.Brands(db)
        competitors.save(db, 'skygen', [offer], brands, now)
        row = db.get(Product, catalog['agilent'])
        first = row.supplier_stock_until
        row.needs_index = False
        competitors.save(db, 'skygen', [offer], brands, now + timedelta(hours=1))
        assert row.supplier_stock and row.needs_index
        assert as_utc(row.supplier_stock_until) == as_utc(first) + timedelta(hours=1)
        docs, _ = build(db, [row], Context(db, False))
        assert docs[0]['stock_valid_until'] == as_utc(row.supplier_stock_until).isoformat()


def test_ambiguous_fixed_sku_never_picks_arbitrary_product(sessions, catalog):
    with sessions.begin() as db:
        brand = db.scalar(select(Brand).where(Brand.slug == 'sigma-aldrich'))
        product(db, brand, 'other-product', packs=('413283-100G',))
        offer = competitors.Offer('ambiguous', 'Sigma-Aldrich', '413283-100G', 'Product',
                                  'https://chimmed-new.ru/products/a', pack='100 g')
        assert competitors.match(db, [(offer, brand.id)]) == {}


def test_reviewed_packaging_allowlist_prevents_hidden_variant_stock(sessions):
    with sessions.begin() as db:
        brand = Brand(slug='usp', name='USP')
        db.add(brand)
        db.flush()
        row = product(db, brand, '1235831', packs=('1235831-1AMP', '1235831-5AMP'))
        packs = list(db.scalars(select(Packaging).where(Packaging.product_id == row.id)
                                .order_by(Packaging.position)))
        row.seo = {'identity': {'review': REVIEW, 'sourceUrl': SOURCE_URL, 'manufacturer': 'USP',
                   'canonicalSlug': MASTER_SLUG, 'canonicalProductId': row.id, 'identifierAliases': ALIASES,
                   'verifiedPackagingId': packs[0].id}}
        hidden = competitors.Offer('hidden', 'USP', '1235831-5AMP', 'Product',
                                   'https://source.test/item', pack='5 ampoules')
        approved = competitors.Offer('approved', 'USP', '1235831-1AMP', 'Product',
                                     'https://source.test/item', pack='1 ampoule')
        assert competitors.match(db, [(hidden, brand.id)]) == {}
        assert competitors.match(db, [(approved, brand.id)]) == {0: (row.id, packs[0].id)}


def test_expiry_runs_even_when_crawling_is_disabled(sessions, catalog, monkeypatch):
    with sessions.begin() as db:
        now = utcnow()
        offer = competitors.Offer('expires', 'Agilent', 'GKSB-312', 'Product',
                                  'https://klad.skygen.com/catalog/a/', quantity=1)
        competitors.save(db, 'skygen', [offer], competitors.Brands(db), now)
        db.execute(update(CompetitorOffer).values(seen_at=now - timedelta(days=11)))
        assert competitors.offers_of(db, catalog['agilent'], now) == []
    monkeypatch.setattr(settings, 'competitor_stock_enabled', False)
    assert competitors.turn(sessions) is None
    assert not flags(sessions)[catalog['agilent']]


def test_fetching_old_declared_stock_does_not_refresh_its_availability(sessions, catalog):
    with sessions.begin() as db:
        now = utcnow()
        offer = competitors.Offer('old-news', 'Agilent', 'GKSB-312', 'Product',
                                  'https://klad.skygen.com/catalog/a/',
                                  stock_updated_at=now - timedelta(days=20))
        competitors.save(db, 'skygen', [offer], competitors.Brands(db), now)
        assert competitors.offers_of(db, catalog['agilent'], now) == []
        assert not db.get(Product, catalog['agilent']).supplier_stock
        competitors.settle(db, now, [], now)
        assert db.scalar(select(func.count()).select_from(CompetitorOffer)) == 1


def test_review_only_stock_does_not_guess_manufacturer_or_article(sessions, catalog):
    with sessions.begin() as db:
        now = utcnow()
        unknown = competitors.Offer('pdf-row', '', '', 'Oxcarbazepine, analytical grade',
                                    'https://source.test/stock.pdf', cas='28721-07-5', pack='100 mg',
                                    review_only=True)
        known = competitors.Offer('review-known', 'Agilent', 'GKSB-312', 'Needs human verification',
                                  'https://source.test/stock.pdf', review_only=True)
        assert competitors.save(db, 'pending', [unknown, known], competitors.Brands(db), now) == (2, 0)
        assert all(o.product_id is None and o.packaging_id is None for o in db.scalars(select(CompetitorOffer)))
        assert not any(p.supplier_stock for p in db.scalars(select(Product)))


def test_pending_review_counter_includes_unresolved_packaging(sessions, catalog):
    with sessions.begin() as db:
        brand = db.scalar(select(Brand).where(Brand.slug == 'agilent'))
        assert brand is not None
        target = product(db, brand, 'PRODUCT-ONLY')
        offer = competitors.Offer('product-only', 'Agilent', 'PRODUCT-ONLY', 'Product without a fixed packaging',
                                  'https://klad.skygen.com/catalog/a/')
        assert competitors.save(db, 'skygen', [offer], competitors.Brands(db), utcnow()) == (1, 1)
        row = db.scalar(select(CompetitorOffer))
        assert row is not None and row.product_id == target.id and row.packaging_id is None
        assert competitors.status(db)['pendingReview'] == 1
        assert not target.supplier_stock and target.supplier_stock_until is None


@pytest.mark.parametrize('tie', ['missing-pack', 'foreign-pack'])
def test_orphan_or_wrong_product_pack_tie_cannot_qualify_public_stock(sessions, catalog, tie):
    with sessions.begin() as db:
        now = utcnow()
        offer = competitors.Offer('invalid-tie', 'Agilent', 'GKSB-312', 'Product',
                                  'https://klad.skygen.com/catalog/a/')
        competitors.save(db, 'skygen', [offer], competitors.Brands(db), now)
        target = db.get(Product, catalog['agilent'])
        assert target is not None and target.supplier_stock
        row = db.scalar(select(CompetitorOffer))
        assert row is not None
        foreign_pack = db.scalar(select(Packaging).where(Packaging.product_id == catalog['waters']))
        assert foreign_pack is not None
        row.packaging_id = 'deleted-pack' if tie == 'missing-pack' else foreign_pack.id
        target.needs_index = False
        db.flush()
        competitors._refresh_flags(db, now)
        assert not target.supplier_stock and target.supplier_stock_until is None and target.needs_index


def test_parser_drift_preserves_last_known_fresh_offers(sessions, sites, catalog):
    competitors.run_all(sessions)
    real = sites.handle

    def handle(request):
        if request.url.host == 'klad.skygen.com' and request.url.path == '/catalog/':
            return httpx.Response(200, text='<html><body>Новая версия сайта</body></html>')
        return real(request)

    sites.handle = handle
    with sessions.begin() as db:
        set_setting(db, 'competitor_results', {'finishedAt': None})
    result = competitors.run_all(sessions)
    assert result is not None
    assert result['sources']['skygen']['incomplete']
    assert not result['sources']['skygen']['complete']
    assert flags(sessions)[catalog['waters']]


def test_truncated_source_does_not_forget_unvisited_offers(sessions, sites, catalog, monkeypatch):
    competitors.run_all(sessions)
    original = competitors.SOURCES['skygen']

    def limited(client, task, wanted):
        page = original(client, task, wanted)
        page.tasks = []
        page.truncated = 1
        return page

    monkeypatch.setitem(competitors.SOURCES, 'skygen', limited)
    with sessions.begin() as db:
        set_setting(db, 'competitor_results', {'finishedAt': None})
    result = competitors.run_all(sessions)
    assert result is not None
    assert not result['sources']['skygen']['complete']
    assert flags(sessions)[catalog['waters']]


def test_robots_disallow_stops_without_requesting_the_catalog(sessions, sites, catalog):
    real = sites.handle

    def handle(request):
        if request.url.host == 'klad.skygen.com':
            sites.calls.append(request)
            assert request.url.path == '/robots.txt'
            return httpx.Response(200, text='User-agent: *\nDisallow: /catalog/\n')
        return real(request)

    sites.handle = handle
    result = competitors.run_all(sessions)
    assert result is not None
    assert result['sources']['skygen']['refused'] == 'robots_disallow'
    assert len([c for c in sites.calls if c.url.host == 'klad.skygen.com']) == 1

