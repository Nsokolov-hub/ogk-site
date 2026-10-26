"""SEO (ADM-07), requests and subscribers (ADM-08), dictionaries (ADM-06), settings (ADM-10), feeds (ADM-11),
the journal (ADM-01)."""

from sqlalchemy import select

from app.admin.models import Redirect
from app.catalog.settings import get_setting
from app.core.config import settings
from app.outbox.models import OutboxEvent
from app.requests.models import SiteRequest
from tests.support import form, submit


def test_redirects_have_no_chains_or_loops(seeded, signed_in, client):
    content = signed_in('content')
    content.ok(content.post('/redirects', {'source': 'https://www.ogk-chem.ru/old/?utm=1', 'target': '/middle/'}))
    content.ok(content.post('/redirects', {'source': '/middle/', 'target': '/final/'}))
    with seeded() as db:
        rows = {r.source: r.target for r in db.scalars(select(Redirect))}
    assert rows == {'/old/': '/final/', '/middle/': '/final/'}
    loop = content.post('/redirects', {'source': '/final/', 'target': '/old/'})
    assert loop.status_code == 422 and loop.json()['code'] == 'REDIRECT_LOOP'
    assert content.post('/redirects', {'source': 'no-slash', 'target': '/x/'}).json()['code'] == 'PATH_INVALID'
    imported = content.ok(content.post('/redirects/import', {'csv': 'откуда;куда;код\n/a/;/b/;302\nbad line\n/c/;/b/'}))
    assert imported['created'] == 2 and len(imported['errors']) == 1
    assert {'source': '/a/', 'target': '/b/', 'code': 302} in client.get('/api/v1/public/redirects').json()
    assert content.ok(content.get('/redirects/check'))['problems'] == []
    exported = content.get('/redirects/export')
    assert exported.status_code == 200 and '/old/;/final/;301' in exported.text


def test_meta_templates_robots_and_the_duplicates_report(seeded, signed_in, client):
    content = signed_in('content')
    templates = {'product': {'ru': {'title': '{name} — {brand} {number} | ОГК-ХИМ'}, 'en': {}},
                 'substance': {'ru': {}, 'en': {}}}
    content.ok(content.put('/seo/templates', {'value': templates}))
    assert client.get('/api/v1/public/site').json()['metaTemplates']['product']['ru']['title'].startswith('{name}')
    bad = content.put('/seo/templates', {'value': {'product': {'ru': {'title': 'Без названия'}}}})
    assert bad.json()['code'] == 'TEMPLATE_INVALID'
    assert content.put('/seo/robots', {'extra': 'Disallow: /'}).json()['code'] == 'ROBOTS_INVALID'
    assert content.put('/seo/robots', {'extra': 'Hello'}).json()['code'] == 'ROBOTS_INVALID'
    content.ok(content.put('/seo/robots', {'extra': 'Disallow: /print/\n# печатные версии'}))
    assert client.get('/api/v1/public/site').json()['robotsExtra'].startswith('Disallow: /print/')
    report = content.ok(content.get('/seo/report'))
    assert report['indexing']['landings'] == 6 and isinstance(report['duplicates'], list)


def test_the_journal_hides_personal_data_from_everyone_but_administrators(seeded, signed_in, client):
    assert submit(client, form()).status_code == 201
    viewer, admin = signed_in('viewer'), signed_in('admin')
    masked = viewer.ok(viewer.get('/requests'))
    row = masked['items'][0]
    assert masked['pii'] is False and '•••' in row['email'] and row['company'] != 'ООО «Пример-Фарма»'
    card = viewer.ok(viewer.get(f'/requests/{row["id"]}'))
    assert 'positions' not in card and 'inn' not in card
    full = admin.ok(admin.get(f'/requests/{row["id"]}'))
    assert full['company'] == 'ООО «Пример-Фарма»' and full['positions'][0]['catalogNumber'] == 'Y0001897'
    assert viewer.post(f'/requests/{row["id"]}/resend').status_code == 403
    with seeded.begin() as db:
        db.get(SiteRequest, row['id']).status = 'failed'
    assert 'очередь' in admin.ok(admin.post(f'/requests/{row["id"]}/resend'))['message']


def test_subscribers_list_and_export_for_administrators(seeded, signed_in, client):
    client.post('/api/v1/public/subscriptions', json={'email': 'a@example.ru', 'personalDataConsent': True,
                                                      'marketingConsent': True})
    admin, content = signed_in('admin'), signed_in('content')
    assert content.get('/subscribers').status_code == 403
    listing = admin.ok(admin.get('/subscribers'))
    assert listing['items'][0]['email'] == 'a@example.ru' and listing['counts'] == {'active': 1}
    exported = admin.get('/subscribers/export')
    assert exported.status_code == 200 and 'a@example.ru' in exported.text


def test_settings_recount_the_catalog_in_the_background(seeded, signed_in, client):
    admin = signed_in('admin')
    settings = admin.ok(admin.get('/settings'))
    assert settings['index_threshold'] == 70 and settings['site']['ru']['phone']
    assert admin.put('/settings/index_threshold', {'value': 140}).status_code == 422
    assert admin.put('/settings/completeness_weights', {'value': {'identity': 50}}).status_code == 422
    admin.ok(admin.put('/settings/index_threshold', {'value': 60}))
    with seeded() as db:
        assert get_setting(db, 'index_threshold') == 60
        assert db.scalar(select(OutboxEvent.kind).where(OutboxEvent.kind == 'catalog.refresh')) == 'catalog.refresh'
    site = settings['site']
    site['ru']['phone'] = {'display': '+7 495 000 00 00', 'href': 'tel:+74950000000'}
    admin.ok(admin.put('/settings/site', {'value': site}))
    assert client.get('/api/v1/public/site').json()['ru']['phone']['display'] == '+7 495 000 00 00'
    assert admin.put('/settings/counters', {'value': {'ym': 'abc'}}).status_code == 422
    admin.ok(admin.put('/settings/counters', {'value': {'ym': '12345678', 'ga': 'G-ABC123'}}))
    assert client.get('/api/v1/public/site').json()['counters'] == {'ym': 12345678, 'ga': 'G-ABC123'}
    catalog = signed_in('catalog')
    assert catalog.put('/settings/index_threshold', {'value': 50}).status_code == 403
    catalog.ok(catalog.put('/settings/feed', {'value': {'categories': ['reagents'], 'brands': []}}))
    check = catalog.ok(catalog.get('/feed/check'))
    assert check['setting']['categories'] == ['reagents'] and any('Цен' in p for p in check['problems'])


def test_dictionaries_and_the_controlled_register(seeded, signed_in, tmp_path):
    catalog = signed_in('catalog')
    current = catalog.ok(catalog.get('/dictionaries'))
    assert {u['key'] for u in current['units']} >= {'mg', 'g', 'ml'}
    refused = catalog.put('/dictionaries/units', {'value': [{'key': 'mg', 'ru': 'мг'}, {'key': 'mg', 'ru': 'мг'}]})
    assert refused.status_code == 422
    saved = catalog.ok(catalog.put('/dictionaries/synonyms', {'value': ['окскарбазепин, oxcarbazepine', ['ацетон', 'acetone']]}))
    assert saved['synonyms'] == [['окскарбазепин', 'oxcarbazepine'], ['ацетон', 'acetone']]
    with seeded() as db:
        assert get_setting(db, 'search_settings_dirty') is True
    from app.catalog.importer.run import write_xlsx

    path = tmp_path / 'register.xlsx'
    write_xlsx(path, [['Перечень', 'Название', 'CAS', 'Синонимы'], ['ПП 964', 'Трамадол', '27203-92-5', 'tramadol']])
    with path.open('rb') as handle:
        result = catalog.ok(catalog.client.post('/api/v1/admin/dictionaries/controlled', headers=catalog.headers,
                                                files={'file': ('register.xlsx', handle)}))
    assert result['entries'] == 1
    assert catalog.ok(catalog.get('/dictionaries/controlled'))['items'][0]['name'] == 'Трамадол'


def test_the_dashboard_and_the_journal_of_changes(seeded, signed_in):
    admin = signed_in('admin')
    admin.ok(admin.post('/redirects', {'source': '/x/', 'target': '/y/'}))
    dashboard = admin.ok(admin.get('/dashboard'))
    assert dashboard['products']['total'] == 413 and 'conflicts' in dashboard['queues']
    assert dashboard['content']['pages'] == 27 and dashboard['integration']['deliveryEnabled'] is True
    journal = admin.ok(admin.get('/audit', params={'entity': 'redirect'}))
    entry = journal['items'][0]
    assert entry['summary'] == '/x/ → /y/ (301)'
    detail = admin.ok(admin.get(f'/audit/{entry["id"]}'))
    assert detail['after']['target'] == '/y/' and detail['before'] is None


def test_letters_follow_the_mail_settings(seeded, signed_in, client, monkeypatch):
    from app.notifications import mail
    from app.outbox import worker

    admin = signed_in('admin')
    admin.ok(admin.put('/settings/mail', {'value': {'sales_email': 'sales@ogk-chem.ru',
                                                   'customer_intro_ru': 'Спасибо! Заявка {number} у нас.'}}))
    assert submit(client, form()).status_code == 201
    letters: list[dict] = []
    monkeypatch.setattr(mail, 'send', lambda to, subject, body, **kw: letters.append({'to': to, 'body': body}))
    monkeypatch.setattr(settings, 'crm_delivery_enabled', False)
    with seeded.begin() as db:
        worker.process_events(db)
    assert any(letter['to'] == ['sales@ogk-chem.ru'] for letter in letters)
    assert any('Спасибо! Заявка S-' in letter['body'] for letter in letters)
