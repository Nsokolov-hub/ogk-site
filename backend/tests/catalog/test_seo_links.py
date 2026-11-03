"""SEO of 03.11.2026: every CAS page is a link away from indexable pages (the index /cas/, the «Вещества» blocks of
categories and brands, the neighbours in the index), brands without a page are not links, IndexNow and the indexing
pilot of chosen brands."""

import httpx
from sqlalchemy import select

from app.catalog import cas_pages, indexnow, pilot
from app.catalog.cas_pages import letter, sort_key
from app.catalog.models import Brand, CasPage, IndexNowUrl, Packaging, Product
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from tests.catalog.test_cas_pages import add

URL = '/api/v1/public'


def test_the_index_sorts_names_as_a_chemist_looks_them_up():
    assert sort_key('DL-Lactic acid') == 'lactic acid'
    assert sort_key('4-Acetamidophenol') == 'acetamidophenol'
    assert sort_key('N,N-Dimethylformamide') == 'dimethylformamide'
    assert sort_key('(S)-Ibuprofen') == sort_key('(±)-Ibuprofen') == 'ibuprofen'
    assert sort_key('D-(+)-Glucose') == 'glucose' and sort_key('17β-Estradiol') == 'estradiol'
    assert sort_key('1H-Indole') == 'indole' and sort_key("2,2'-Bipyridine") == 'bipyridine'
    # A name that only looks like a prefix stays whole.
    assert sort_key('Nicotinamide') == 'nicotinamide' and sort_key('Sodium chloride') == 'sodium chloride'
    assert letter('lactic acid') == 'l' and letter('ωx') == '0' and letter(None) == '0'


def substances(db) -> None:
    """Three CAS pages: two in reagents (Macklin and Aozeal), one in the EDQM standards (EDQM and USP)."""
    for n, (cas, name) in enumerate([('50-21-5', 'DL-Lactic acid'), ('64-17-5', 'Ethanol')]):
        add(db, 'macklin', f'M-{n}', name, cas)
        add(db, 'aozeal', f'A-{n}', name, cas)
        add(db, 'aozeal', f'A-{n}b', name, cas)
    add(db, 'edqm', 'E-1', 'Ibuprofen for peak identification CRS', '15687-27-2', 'reference-standards/edqm')
    add(db, 'usp', 'U-1', 'Ibuprofen Related Compound', '15687-27-2', 'reference-standards/usp')
    add(db, 'usp', 'U-2', 'Ibuprofen Related Compound', '15687-27-2', 'reference-standards/usp')


def test_the_build_links_cas_pages_from_categories_and_brands(seeded):
    with seeded.begin() as db:
        substances(db)
    counts = cas_pages.build(seeded)
    assert counts['pages'] == 3
    with seeded() as db:
        keys = {row.cas: row.sort_key for row in db.scalars(select(CasPage))}
        links = get_setting(db, 'cas_links')
        queued = set(db.scalars(select(IndexNowUrl.path)))
    assert keys['50-21-5'] == 'lactic acid'
    # A category lists its own substances; its parent gets those of all children.
    assert set(links['categories']['reagents']) == {'50-21-5', '64-17-5'}
    assert links['categories']['reference-standards/edqm'] == ['15687-27-2']
    assert '15687-27-2' in links['categories']['reference-standards']
    assert set(links['brands']['aozeal']) == {'50-21-5', '64-17-5'} and links['brands']['usp'] == ['15687-27-2']
    # New pages go to IndexNow; a second build has nothing new to announce.
    assert queued == {'/cas/50-21-5/', '/cas/64-17-5/', '/cas/15687-27-2/'}
    assert cas_pages.build(seeded)['queued'] == 0


def test_the_index_and_the_blocks_in_the_public_api(client, seeded):
    with seeded.begin() as db:
        substances(db)
    cas_pages.build(seeded)
    index = client.get(f'{URL}/cas/index').json()
    assert index['total'] == 3
    assert {(x['letter'], x['count']) for x in index['letters']} == {('e', 1), ('i', 1), ('l', 1)}
    offers = [x['offers'] for x in index['popular']]
    assert len(offers) == 3 and offers == sorted(offers, reverse=True)
    page = client.get(f'{URL}/cas/index/l').json()
    assert [i['cas'] for i in page['items']] == ['50-21-5'] and page['pageCount'] == 1
    assert client.get(f'{URL}/cas/index/q').status_code == 404
    assert client.get(f'{URL}/cas/index/ab').status_code == 404
    assert client.get(f'{URL}/cas/index/l?page=2').status_code == 404
    # The CAS page names its letter and its neighbours in the index (ethanol < ibuprofen < lactic acid).
    data = client.get(f'{URL}/cas/15687-27-2').json()
    assert data['page']['letter'] == 'i'
    assert [n['cas'] for n in data['neighbours']] == ['64-17-5', '50-21-5']
    category = client.get(f'{URL}/catalog/category', params={'path': 'reagents'}).json()
    assert {c['cas'] for c in category['casPages']} == {'50-21-5', '64-17-5'}
    assert client.get(f'{URL}/catalog/category', params={'path': ''}).json()['casPages']
    brand = client.get(f'{URL}/brands/usp').json()
    assert [c['cas'] for c in brand['casPages']] == ['15687-27-2']


def test_our_russian_names_show_and_the_source_names_never_do(client, seeded):
    with seeded.begin() as db:
        substances(db)
        for product in db.scalars(select(Product).where(Product.cas == '50-21-5')):
            product.source_name = 'Кислота молочная, ч.'
        set_setting(db, 'cas_names_ru', {'50-21-5': 'Молочная кислота'})
    cas_pages.build(seeded)
    data = client.get(f'{URL}/cas/50-21-5').json()
    assert data['page']['nameRu'] == 'Молочная кислота'
    assert 'Кислота молочная, ч.' not in client.get(f'{URL}/cas/50-21-5').text
    assert client.get(f'{URL}/cas/index/l').json()['items'][0]['nameRu'] == 'Молочная кислота'


def test_only_brands_with_a_page_are_links(client, seeded):
    with seeded.begin() as db:
        db.add(Brand(slug='abcr', name='ABCR', page_published=False, content={}))
        db.flush()
        add(db, 'abcr', 'AB-1', 'Ethanol', '64-17-5')
        add(db, 'macklin', 'M-1', 'Ethanol', '64-17-5')
        add(db, 'aozeal', 'A-1', 'Ethanol', '64-17-5')
    cas_pages.build(seeded)
    items = {i['brand']['slug']: i['brand']['page'] for i in client.get(f'{URL}/cas/64-17-5').json()['items']}
    assert items['abcr'] is False and items['macklin'] is True and items['aozeal'] is True
    assert client.get(f'{URL}/products/abcr-ab-1').json()['product']['brand']['page'] is False
    assert client.get(f'{URL}/products/macklin-m-1').json()['product']['brand']['page'] is True


def test_the_queue_keeps_russian_public_pages_once(sessions):
    with sessions.begin() as db:
        assert indexnow.queue(db, ['/cas/1/', f'{settings.site_url}/cas/1/', '/en/cas/1/', '/admin/x', '/search/?q=1',
                                   'https://example.com/x', '/brands/usp/']) == 2
        assert indexnow.queue(db, ['/brands/usp/']) == 0
    with sessions() as db:
        assert set(db.scalars(select(IndexNowUrl.path))) == {'/cas/1/', '/brands/usp/'}


def test_the_worker_sends_the_queue_and_keeps_it_on_a_refusal(sessions, monkeypatch):
    sent: list[dict] = []

    def answer(status: int):
        def handler(request: httpx.Request) -> httpx.Response:
            import json

            sent.append(json.loads(request.content))
            return httpx.Response(status)
        return httpx.MockTransport(handler)

    with sessions.begin() as db:
        indexnow.queue(db, ['/cas/1/', '/brands/usp/'])
    assert not indexnow.enabled()  # tests run as development: the worker never sends
    assert indexnow.send(sessions, transport=answer(403)) == 0
    with sessions() as db:
        assert db.scalar(select(IndexNowUrl).limit(1)) is not None
        assert not indexnow.due(db)
    assert indexnow.send(sessions, transport=answer(202)) == 2
    body = sent[-1]
    assert body['host'] == 'www.ogk-chem.ru' and body['key'] == settings.indexnow_key
    assert body['keyLocation'] == f'{settings.site_url}/{settings.indexnow_key}.txt'
    assert sorted(body['urlList']) == [f'{settings.site_url}/brands/usp/', f'{settings.site_url}/cas/1/']
    with sessions() as db:
        assert db.scalar(select(IndexNowUrl).limit(1)) is None
    monkeypatch.setattr(settings, 'environment', 'production')
    assert indexnow.enabled()


def test_the_key_file_of_the_storefront_is_the_key():
    from pathlib import Path

    public = Path(__file__).resolve().parents[3] / 'public' / f'{settings.indexnow_key}.txt'
    assert public.read_text().strip() == settings.indexnow_key


def test_a_publication_in_the_admin_goes_to_indexnow(seeded):
    from app.admin import editables

    with seeded.begin() as db:
        brand = db.scalar(select(Brand).where(Brand.slug == 'usp'))
        payload = editables.BrandEditable().payload(db, brand)
        editables.publish(db, None, 'brand', brand.id, payload)
    with seeded() as db:
        assert '/brands/usp/' in set(db.scalars(select(IndexNowUrl.path)))


def test_the_pilot_opens_real_cards_of_chosen_brands_and_undo_gives_them_back(seeded):
    with seeded.begin() as db:
        db.add(Brand(slug='pilotlab', name='PilotLab', page_published=False, content={}))
        db.flush()
        real = add(db, 'pilotlab', 'P-1', 'Paracetamol Reference Standard', '103-90-2')
        stand = add(db, 'pilotlab', 'P-2', 'PilotLab P-2', '103-90-3')  # the importer's stand-in name
        bare = add(db, 'pilotlab', 'P-3', 'Some Standard', None)  # neither a CAS nor column values
        nopack = add(db, 'pilotlab', 'P-4', 'Caffeine Reference Standard', '58-08-2')
        for product in (real, stand, bare):
            db.add(Packaging(product_id=product.id, key='100-mg', label_ru='100 мг', label_en='100 mg'))
        ids = [real.id, stand.id, bare.id, nopack.id]
    with seeded.begin() as db:
        counts, queued = pilot.open_cards(db, ['pilotlab'], 10)
    assert counts == {'pilotlab': 1} and queued == 1
    with seeded() as db:
        rows = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids)))}
        assert rows[real.id].indexable and rows[real.id].index_override is True and rows[real.id].seo['pilot']
        assert not any(rows[i].indexable for i in ids[1:])
    with seeded.begin() as db:
        assert pilot.undo(db, ['pilotlab'])[0] == {'pilotlab': 1}
        try:
            pilot.open_cards(db, ['no-such-brand'], 1)
        except pilot.UnknownBrands:
            pass
        else:
            raise AssertionError('an unknown brand must stop the pilot')
    with seeded() as db:
        product = db.get(Product, real.id)
        assert product.index_override is None and 'pilot' not in product.seo and not product.indexable
