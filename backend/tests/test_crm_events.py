"""Events of the CRM (flow F2): signed, applied once; stages become offline conversions (F3), published
positions become cards waiting for moderation (F4), registry changes start the brands load (F5)."""

import hashlib
import hmac
import json
import time
from decimal import Decimal
from email.parser import BytesParser
from email.policy import default
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from app.catalog.models import Brand, BrandAlias, Packaging, Product
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.crm import conversions
from app.outbox import worker
from app.outbox.models import OutboxEvent
from app.requests.models import SiteRequest
from tests.support import attribution_cookie, form, submit

SECRET = 'crm-events-secret'
URL = '/api/v1/crm/events'


@pytest.fixture(autouse=True)
def events_on(monkeypatch):
    monkeypatch.setattr(settings, 'crm_events_secret', SECRET)
    monkeypatch.setattr(settings, 'crm_events_allowed_ips', '')
    monkeypatch.setattr(settings, 'ym_counter_id', '98765')
    monkeypatch.setattr(settings, 'metrika_oauth_token', 'ym-token')
    monkeypatch.setattr(settings, 'ga_measurement_id', 'G-TEST1')
    monkeypatch.setattr(settings, 'ga_api_secret', 'ga-secret')


def send(client, kind: str, data: dict, *, event_id: str | None = None, secret: str = SECRET,
         stamp: int | None = None):
    event_id = event_id or str(uuid4())
    body = json.dumps({'id': event_id, 'type': kind, 'occurred_at': '2026-10-26T10:00:00Z', 'data': data},
                      ensure_ascii=False, separators=(',', ':')).encode()
    moment = str(stamp if stamp is not None else int(time.time()))
    signature = 'sha256=' + hmac.new(secret.encode(), moment.encode() + b'.' + body, hashlib.sha256).hexdigest()
    return client.post(URL, content=body, headers={'Content-Type': 'application/json', 'X-CRM-Event-Id': event_id,
                                                   'X-CRM-Timestamp': moment, 'X-CRM-Signature': signature})


def site_request(client, *, cookies: dict[str, str] | None = None) -> str:
    answer = submit(client, form(), cookies=cookies)
    assert answer.status_code == 201, answer.text
    return answer.json()['siteRequestId']


def outbox(sessions, prefix: str) -> list[OutboxEvent]:
    with sessions() as db:
        return list(db.scalars(select(OutboxEvent).where(OutboxEvent.kind.like(prefix + '%'))
                               .order_by(OutboxEvent.event_key)))


VISITOR = {'_ym_uid': '1698765432123456789', '_ga': 'GA1.1.1234567890.1698765432',
           'ogk_attr': attribution_cookie({'utm_source': 'yandex', 'utm_medium': 'cpc', 'yclid': '777'})}


def test_signature_time_and_address_are_checked(client, monkeypatch):
    assert send(client, 'manufacturer.upserted', {'id': 'm'}, secret='wrong').status_code == 401
    assert send(client, 'manufacturer.upserted', {'id': 'm'}, stamp=int(time.time()) - 3600).status_code == 401
    monkeypatch.setattr(settings, 'crm_events_allowed_ips', '10.20.0.0/16')
    assert send(client, 'manufacturer.upserted', {'id': 'm'}).status_code == 403
    monkeypatch.setattr(settings, 'crm_events_allowed_ips', '')
    monkeypatch.setattr(settings, 'crm_events_secret', '')
    assert send(client, 'manufacturer.upserted', {'id': 'm'}).status_code == 503


def test_unknown_types_and_requests_are_accepted_and_ignored(client):
    assert send(client, 'something.new', {}).json() == {'ok': True, 'ignored': 'UNKNOWN_TYPE'}
    answer = send(client, 'site_request.assigned', {'site_request_id': 'nope', 'status': 'in_work'})
    assert answer.status_code == 200 and answer.json()['ignored'] == 'SITE_REQUEST_UNKNOWN'


def test_fate_and_stages_of_a_site_request_with_offline_conversions(client, sessions):
    request_id = site_request(client, cookies=VISITOR)
    assert send(client, 'site_request.converted', {'site_request_id': request_id, 'status': 'converted',
                                                   'crm_request_id': 'r-1'}).status_code == 200
    base = {'site_request_id': request_id, 'crm_request_id': 'r-1', 'crm_request_number': 'З-2026-0042'}
    assert send(client, 'request.stage_changed', {**base, 'stage': 'collecting_quotes'}).json()['conversions'] == 2
    # A sale implies the earlier goals: only the new one is queued, for both counters.
    sale = send(client, 'request.stage_changed', {**base, 'stage': 'sale_confirmed',
                                                  'revenue': {'amount': '15400.50', 'currency': 'RUB'}})
    assert sale.json()['conversions'] == 4
    with sessions() as db:
        row = db.get(SiteRequest, request_id)
        assert (row.crm_status, row.crm_stage, row.crm_request_number) == ('converted', 'sale_confirmed',
                                                                         'З-2026-0042')
        assert (row.sale_amount, row.sale_currency) == (Decimal('15400.50'), 'RUB')
    keys = [e.event_key.rsplit(':', 1)[1] + '/' + e.kind for e in outbox(sessions, 'conversion.')]
    assert sorted(keys) == sorted(f'{goal}/conversion.{system}' for goal in ('qualified', 'proposal', 'sale')
                                  for system in ('metrika', 'ga4'))
    calls: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={'uploading': {'id': 1}}) if 'metrika' in str(request.url) \
            else httpx.Response(204)

    original = conversions.http_client
    conversions.http_client = lambda: httpx.Client(transport=httpx.MockTransport(answer))
    try:
        with sessions.begin() as db:
            counts = worker.process_events(db)
    finally:
        conversions.http_client = original
    assert counts['failed'] == 0
    metrika = [c for c in calls if 'metrika' in str(c.url)]
    ga = [c for c in calls if 'google-analytics' in str(c.url)]
    assert len(metrika) == 3 and len(ga) == 3
    sale_upload = next(c for c in metrika if b'crm_sale' in c.content)
    assert sale_upload.headers['Authorization'] == 'OAuth ym-token'
    assert sale_upload.url.params['client_id_type'] == 'CLIENT_ID' and '/counter/98765/' in str(sale_upload.url)
    head = f'Content-Type: {sale_upload.headers["Content-Type"]}\r\n\r\n'.encode()
    csv_text = next(BytesParser(policy=default).parsebytes(head + sale_upload.content).iter_parts()).get_content()
    lines = csv_text.strip().splitlines()
    assert lines[0] == 'ClientId,Target,DateTime,Price,Currency'
    assert lines[1].startswith('1698765432123456789,crm_sale,') and lines[1].endswith(',15400.50,RUB')
    ga_sale = next(json.loads(c.content) for c in ga if b'close_convert_lead' in c.content)
    assert ga_sale['client_id'] == '1234567890.1698765432'
    assert ga_sale['events'][0]['params']['value'] == 15400.5
    assert ga[0].url.params['api_secret'] == 'ga-secret' and ga[0].url.params['measurement_id'] == 'G-TEST1'
    # Nothing personal leaves the site.
    sent = b''.join(c.content for c in calls)
    assert b'zakupki' not in sent and 'Пример'.encode() not in sent


def test_conversions_need_a_known_visitor_and_the_keys(client, sessions, monkeypatch):
    anonymous = site_request(client)
    base = {'site_request_id': anonymous, 'crm_request_id': 'r-2', 'stage': 'proposal_sent'}
    assert send(client, 'request.stage_changed', base).json()['conversions'] == 0
    monkeypatch.setattr(settings, 'metrika_oauth_token', '')
    known = site_request(client, cookies=VISITOR)
    assert send(client, 'request.stage_changed', {**base, 'site_request_id': known}).json()['conversions'] == 2
    assert {e.kind for e in outbox(sessions, 'conversion.')} == {'conversion.ga4'}


def test_a_repeated_event_is_applied_once(client, sessions):
    request_id = site_request(client, cookies=VISITOR)
    event_id = str(uuid4())
    data = {'site_request_id': request_id, 'crm_request_id': 'r-3', 'stage': 'collecting_quotes'}
    first = send(client, 'request.stage_changed', data, event_id=event_id).json()
    assert send(client, 'request.stage_changed', data, event_id=event_id).json() == first
    with sessions() as db:
        assert db.get(SiteRequest, request_id).version == 2


def test_closed_and_lost(client, sessions):
    request_id = site_request(client)
    send(client, 'request.closed', {'site_request_id': request_id, 'stage': 'proposal_sent', 'lost': True})
    with sessions() as db:
        assert db.get(SiteRequest, request_id).crm_stage == 'lost'


def product_event(**changes) -> dict:
    data = {'crm_product_id': 'nom-1', 'site_product_id': None, 'publish': True, 'active': True, 'brand': 'EDQM',
            'crm_manufacturer_id': 'man-1', 'catalog_number': 'Y0001897', 'name': 'Oxcarbazepine CRS',
            'cas': '28721-07-5', 'purity': None, 'packagings': ['100 мг', '1 г']}
    data.update(changes)
    return data


def test_a_published_position_becomes_a_card_waiting_for_moderation(client, sessions):
    answer = send(client, 'product.upserted', product_event())
    assert answer.status_code == 200, answer.text
    site_id = answer.json()['site_product_id']
    with sessions() as db:
        product = db.get(Product, site_id)
        assert (product.status, product.source, product.crm_product_id, product.cas) == (
            'moderation', 'crm', 'nom-1', '28721-07-5')
        brand = db.get(Brand, product.brand_id)
        assert (brand.name, brand.crm_manufacturer_id, brand.page_published) == ('EDQM', 'man-1', False)
        assert db.scalar(select(BrandAlias.source).where(BrandAlias.brand_id == brand.id)) == 'crm'
        assert sorted(db.scalars(select(Packaging.key).where(Packaging.product_id == site_id))) == ['1-g', '100-mg']
        assert product.indexable is False
    # The same position again (now with the site's id) changes nothing but fills the gaps.
    again = send(client, 'product.upserted', product_event(site_product_id=site_id, purity='≥ 98 %',
                                                           packagings=['100 мг', '1 г', '5 г']))
    assert again.json()['site_product_id'] == site_id
    with sessions() as db:
        assert db.get(Product, site_id).purity == '≥ 98 %'
        assert len(list(db.scalars(select(Packaging).where(Packaging.product_id == site_id)))) == 3
    # Unticked before moderation: the card leaves the queue.
    send(client, 'product.upserted', product_event(site_product_id=site_id, publish=False))
    with sessions() as db:
        assert db.get(Product, site_id).status == 'draft'


def test_a_position_the_site_already_has_is_linked_not_duplicated(client, sessions):
    with sessions.begin() as db:
        brand = Brand(slug='edqm', name='EDQM', content={})
        db.add(brand)
        db.flush()
        db.add(BrandAlias(brand_id=brand.id, name='EDQM', normalized='edqm', source='seed'))
        product = Product(brand_id=brand.id, catalog_number='Y0001897', catalog_number_norm='y0001897',
                          slug='edqm-y0001897', name_en='Oxcarbazepine CRS', status='published', source='seed',
                          purity='Ph. Eur.', manual_fields=['purity'])
        db.add(product)
        db.flush()
        existing = product.id
    answer = send(client, 'product.upserted', product_event(crm_manufacturer_id='man-9', purity='99 %'))
    assert answer.json() == {'ok': True, 'site_product_id': existing}
    with sessions() as db:
        product = db.get(Product, existing)
        assert (product.crm_product_id, product.status, product.purity) == ('nom-1', 'published', 'Ph. Eur.')
        assert db.scalar(select(Brand.id).where(Brand.crm_manufacturer_id == 'man-9')) is None


def test_positions_the_site_cannot_place_are_ignored(client):
    assert send(client, 'product.upserted', product_event(publish=False)).json()['ignored'] == 'NOT_PUBLISHED'
    assert send(client, 'product.upserted', product_event(catalog_number=None)).json()['ignored'] == \
        'NO_CATALOG_NUMBER'
    assert send(client, 'product.upserted', product_event(brand='', crm_manufacturer_id=None)).json()['ignored'] == \
        'NO_BRAND'
    assert send(client, 'product.upserted', {'publish': True}).status_code == 422


def test_registry_changes_start_the_brands_load(client, sessions):
    with sessions.begin() as db:
        set_setting(db, 'brands_sync_run_at', '2026-10-26T03:00:00+00:00')
    assert send(client, 'manufacturer.merged', {'id': 'a', 'merged_into_id': 'b'}).status_code == 200
    with sessions() as db:
        assert get_setting(db, 'brands_sync_run_at') is None
