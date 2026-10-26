"""Pages, categories, brands, substances and landings through drafts (ADM-02): preview, publish, schedule, restore."""

from datetime import timedelta

from sqlalchemy import select, update

from app.admin import editables
from app.admin.models import ContentPage, Draft, Redirect
from app.catalog.models import Brand, Category, Product, Substance
from app.catalog.settings import get_setting
from app.core.db import utcnow
from app.outbox.models import OutboxEvent


def page_id(db, kind: str, slug: str) -> str:
    return db.scalar(select(ContentPage.id).where(ContentPage.kind == kind, ContentPage.slug == slug))


def test_the_site_texts_are_served_from_the_database(client, seeded):
    services = client.get('/api/v1/public/pages', params={'kind': 'service'}).json()
    assert len(services) == 7 and services[0]['content']['ru']['h1']
    page = client.get('/api/v1/public/pages/service/cold-chain').json()
    assert page['content']['ru']['slug'] == 'cold-chain' and page['content']['en']['h1'] and page['preview'] is False
    site = client.get('/api/v1/public/site').json()
    assert site['ru']['phone']['display'] == '+7 495 234 28 63' and site['en']['legal']['name'] == 'OGK-CHEM LLC'
    assert len(client.get('/api/v1/public/landings').json()) == 6
    landing = client.get('/api/v1/public/landing', params={'path': 'chromatography/hplc-columns',
                                                          'slug': 'waters-c18'}).json()
    assert landing['preset'] == {'brand': ['waters'], 'phase': ['C18']}
    assert client.get('/api/v1/public/pages/service/nope').status_code == 404


def test_draft_preview_and_publication(seeded, signed_in):
    content = signed_in('content')
    with seeded() as db:
        target = page_id(db, 'service', 'cold-chain')
    view = content.ok(content.get(f'/edit/page/{target}'))
    data = view['published']
    data['content']['ru']['h1'] = 'Холодовая цепь: новый заголовок'
    saved = content.ok(content.put(f'/edit/page/{target}/draft', {'data': data}))
    assert saved['draft']['content']['ru']['h1'] == 'Холодовая цепь: новый заголовок'
    public = content.client.get('/api/v1/public/pages/service/cold-chain')
    assert public.json()['content']['ru']['h1'] != 'Холодовая цепь: новый заголовок'
    token = saved['previewUrl'].split('preview=')[1]
    preview = content.client.get('/api/v1/public/pages/service/cold-chain', params={'preview': token})
    assert preview.json()['content']['ru']['h1'] == 'Холодовая цепь: новый заголовок'
    assert preview.json()['preview'] is True and preview.headers['cache-control'] == 'no-store'
    other = editables.preview_token('page', 'another-id')
    assert content.client.get('/api/v1/public/pages/service/cold-chain', params={'preview': other}) \
        .json()['preview'] is False
    published = content.ok(content.post(f'/edit/page/{target}/publish', {}))
    assert published['draft'] is None and published['history'][0]['action'] == 'publish'
    assert content.client.get('/api/v1/public/pages/service/cold-chain').json()['content']['ru']['h1'] == \
        'Холодовая цепь: новый заголовок'
    with seeded() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.kind == 'storefront.revalidate'))
        assert 'page:service:cold-chain' in event.payload['tags']
        row = db.get(ContentPage, target)
        assert row.content['ru']['updatedAt'] == utcnow().date().isoformat()


def test_invalid_drafts_are_refused_with_the_field(seeded, signed_in):
    content = signed_in('content')
    with seeded() as db:
        target = page_id(db, 'service', 'tn-ved')
    data = content.ok(content.get(f'/edit/page/{target}'))['published']
    data['content']['ru']['title'] = ''
    refused = content.put(f'/edit/page/{target}/draft', {'data': data})
    assert refused.status_code == 422 and refused.json()['field'] == 'title'
    data['content']['ru']['title'] = 'Коды ТН ВЭД'
    data['content']['en'] = {'h1': 'TN VED'}
    assert content.put(f'/edit/page/{target}/draft', {'data': data}).json()['message'].startswith('EN')


def test_scheduled_publication_and_restoring_a_version(seeded, signed_in):
    content = signed_in('content')
    with seeded() as db:
        target = page_id(db, 'article', 'edqm-vs-usp')
    original = content.ok(content.get(f'/edit/page/{target}'))['published']
    changed = {**original, 'content': {**original['content'], 'ru': {**original['content']['ru'], 'lead': 'Новое'}}}
    content.ok(content.put(f'/edit/page/{target}/draft', {'data': changed}))
    later = (utcnow() + timedelta(hours=3)).isoformat()
    scheduled = content.ok(content.post(f'/edit/page/{target}/publish', {'at': later}))
    assert scheduled['publishAt'] and scheduled['draft']['content']['ru']['lead'] == 'Новое'
    with seeded.begin() as db:
        assert editables.publish_due(db) == 0
        db.scalar(select(Draft)).publish_at = utcnow() - timedelta(minutes=1)
    with seeded.begin() as db:
        assert editables.publish_due(db) == 1
    view = content.ok(content.get(f'/edit/page/{target}'))
    assert view['published']['content']['ru']['lead'] == 'Новое' and view['history'][0]['action'] == 'publish_scheduled'
    entry = view['history'][0]['id']
    content.ok(content.put(f'/edit/page/{target}/draft', {'data': original}))
    content.ok(content.post(f'/edit/page/{target}/publish', {}))
    restored = content.ok(content.post(f'/edit/page/{target}/restore/{entry}'))
    assert restored['draft']['content']['ru']['lead'] == 'Новое'


def test_a_new_address_answers_301_from_the_old_one(seeded, signed_in, client):
    content = signed_in('content')
    with seeded() as db:
        target = page_id(db, 'solution', 'hplc-laboratory')
    data = content.ok(content.get(f'/edit/page/{target}'))['published']
    content.ok(content.put(f'/edit/page/{target}/draft', {'data': {**data, 'slug': 'hplc-lab'}}))
    content.ok(content.post(f'/edit/page/{target}/publish', {}))
    assert client.get('/api/v1/public/pages/solution/hplc-laboratory').json() == {'moved': '/solutions/hplc-lab/'}
    redirects = client.get('/api/v1/public/redirects').json()
    assert {'source': '/solutions/hplc-laboratory/', 'target': '/solutions/hplc-lab/', 'code': 301} in redirects
    data = content.ok(content.get(f'/edit/page/{target}'))['published']
    content.ok(content.put(f'/edit/page/{target}/draft', {'data': {**data, 'slug': 'hplc-laboratory'}}))
    content.ok(content.post(f'/edit/page/{target}/publish', {}))
    with seeded() as db:
        rows = {r.source: r.target for r in db.scalars(select(Redirect))}
    # Back to the first address: no loop, the new old one points to it.
    assert rows == {'/solutions/hplc-lab/': '/solutions/hplc-laboratory/'}


def test_new_pages_start_hidden_with_the_kinds_fields(seeded, signed_in, client):
    content = signed_in('content')
    created = content.ok(content.post('/pages', {'kind': 'article', 'slug': 'Kak vybrat kolonku',
                                                 'title': 'Как выбрать колонку'}))
    assert created['published']['status'] == 'hidden' and created['draft']['slug'] == 'kak-vybrat-kolonku'
    assert set(created['draft']['content']['ru']) >= {'h1', 'lead', 'body', 'cta', 'authorSlug'}
    assert client.get('/api/v1/public/pages/article/kak-vybrat-kolonku').status_code == 404
    refused = content.post(f'/edit/page/{created["id"]}/publish', {})
    assert refused.status_code == 422
    data = created['draft']
    data['content']['ru'].update({'description': 'Как подобрать колонку для ВЭЖХ', 'publishedAt': '2026-10-26',
                                  'authorSlug': 'timur-gilmutdinov',
                                  'body': [{'type': 'p', 'text': 'Начните с методики.'}],
                                  'cta': {'title': 'Подберём', 'text': '', 'href': '/rfq/', 'label': 'Запрос'}})
    content.ok(content.put(f'/edit/page/{created["id"]}/draft', {'data': data}))
    content.ok(content.post(f'/edit/page/{created["id"]}/publish', {}))
    assert client.get('/api/v1/public/pages/article/kak-vybrat-kolonku').json()['content']['ru']['body'][0]['text']
    assert content.post('/pages', {'kind': 'home', 'slug': 'x', 'title': 'Вторая главная'}).status_code == 422


def test_categories_brands_and_substances_through_the_editor(seeded, signed_in, client):
    catalog, content = signed_in('catalog'), signed_in('content')
    with seeded() as db:
        category = db.scalar(select(Category).where(Category.path == 'reference-standards/edqm'))
        brand = db.scalar(select(Brand).where(Brand.slug == 'edqm'))
        substance = db.scalar(select(Substance).where(Substance.slug == 'oxcarbazepine'))
        assert category and brand and substance
        ids = category.id, brand.id, substance.id
    data = catalog.ok(catalog.get(f'/edit/category/{ids[0]}'))['published']
    data['content']['ru']['intro'] = 'Новое вступление EDQM'
    data['facets'] = ['brand', 'pack']
    saved = catalog.ok(catalog.put(f'/edit/category/{ids[0]}/draft', {'data': data}))
    token = saved['previewUrl'].split('preview=')[1]
    preview = client.get('/api/v1/public/catalog/category', params={'path': 'reference-standards/edqm',
                                                                     'preview': token}).json()
    assert preview['content']['ru']['intro'] == 'Новое вступление EDQM' and preview['facets'] == ['brand', 'pack']
    catalog.ok(catalog.post(f'/edit/category/{ids[0]}/publish', {}))
    assert client.get('/api/v1/public/catalog/category', params={'path': 'reference-standards/edqm'}) \
        .json()['content']['ru']['facets'] == ['brand', 'pack']

    with seeded.begin() as db:
        db.execute(update(Product).values(needs_index=False))
    data = catalog.ok(catalog.get(f'/edit/brand/{ids[1]}'))['published']
    catalog.ok(catalog.put(f'/edit/brand/{ids[1]}/draft', {'data': {**data, 'customPackaging': True}}))
    catalog.ok(catalog.post(f'/edit/brand/{ids[1]}/publish', {}))
    with seeded() as db:
        assert db.scalar(select(Product.needs_index).where(Product.brand_id == ids[1]).limit(1)) is True

    data = content.ok(content.get(f'/edit/substance/{ids[2]}'))['published']
    content.ok(content.put(f'/edit/substance/{ids[2]}/draft',
                           {'data': {**data, 'synonyms': [*data['synonyms'], 'оксибазепин']}}))
    content.ok(content.post(f'/edit/substance/{ids[2]}/publish', {}))
    with seeded() as db:
        assert get_setting(db, 'search_settings_dirty') is True
    assert signed_in('viewer').put(f'/edit/brand/{ids[1]}/draft', {'data': data}).status_code == 403
    assert catalog.put('/edit/page/x/draft', {'data': {}}).status_code == 403


def test_landings_are_created_hidden_and_published(seeded, signed_in, client):
    content = signed_in('content')
    created = content.ok(content.post('/landings', {'categoryPath': 'chromatography/hplc-columns',
                                                    'slug': 'phenomenex-c18', 'name': 'Phenomenex C18',
                                                    'filters': {'brand': ['phenomenex'], 'phase': ['C18']}}))
    assert client.get('/api/v1/public/landing', params={'path': 'chromatography/hplc-columns',
                                                       'slug': 'phenomenex-c18'}).status_code == 404
    data = created['published']
    data['status'] = 'published'
    data['content']['ru'].update({'h1': 'Колонки Phenomenex C18', 'title': 'Колонки Phenomenex C18 | ОГК-ХИМ',
                                  'description': 'Колонки Phenomenex C18 для ВЭЖХ'})
    content.ok(content.put(f'/edit/landing/{created["id"]}/draft', {'data': data}))
    content.ok(content.post(f'/edit/landing/{created["id"]}/publish', {}))
    found = client.get('/api/v1/public/landing', params={'path': 'chromatography/hplc-columns',
                                                         'slug': 'phenomenex-c18'}).json()
    assert found['content']['ru']['name'] == 'Phenomenex C18'
    clash = content.post('/landings', {'categoryPath': 'chromatography', 'slug': 'hplc-columns', 'name': 'x'})
    assert clash.status_code in (200, 409)
    listing = content.ok(content.get('/landings'))['items']
    assert any(item['slug'] == 'phenomenex-c18' for item in listing)
