"""Freeze private stock when accepting the request, independent of browser claims and retry timing."""

import json
from uuid import uuid4

from sqlalchemy import select

from app.crm.client import payload
from app.notifications.texts import alert_letter, customer_letter, sales_letter
from app.requests import service
from app.requests.models import SiteRequest, SiteRequestItem
from app.requests.repeat import resolve, token_for
from tests.support import form, submit


def test_stock_is_server_generated_and_frozen_before_delivery(client, sessions, monkeypatch):
    captured = []

    def capture(db, item, now):
        captured.append(item)
        return {
            'version': 1, 'captured_at': now.isoformat(), 'availability': 'in_stock', 'origin': 'supplier',
            'site_product_id': item['site_product_id'], 'site_packaging_id': item['site_packaging_id'],
            'packaging_match': 'exact',
            'offers': [{'source': 'chimmed', 'source_name': 'Химмед', 'offer_id': 'offer-1',
                        'external_id': 'external-1', 'catalog_number': item['catalog_number'], 'pack': item['packaging'],
                        'site_packaging_id': item['site_packaging_id'], 'match': 'exact_pack',
                        'seen_at': now.isoformat(), 'valid_until': now.isoformat(), 'quantity': None,
                        'url': 'https://chimmed.test/offer'}],
        }

    monkeypatch.setattr(service, 'capture_stock', capture)
    body = form()
    body['items'][0].update(sitePackagingId='pack-1', stockSnapshot={'origin': 'own', 'forged': True})
    key = str(uuid4())
    first = submit(client, body, key=key)
    assert first.status_code == 201, first.text
    assert set(first.json()) == {'siteRequestId', 'number'}
    assert len(captured) == 1 and captured[0]['site_packaging_id'] == 'pack-1'
    assert 'stock_snapshot' not in captured[0]
    with sessions() as db:
        row = db.get(SiteRequest, first.json()['siteRequestId'])
        item = db.scalar(select(SiteRequestItem).where(SiteRequestItem.request_id == row.id))
        original = item.stock_snapshot
        assert original['origin'] == 'supplier' and item.site_packaging_id == 'pack-1'
        outbound, _ = payload(db, row)
        assert outbound['items'][0]['stock_snapshot'] == original
        assert outbound['items'][0]['site_packaging_id'] == 'pack-1'
        assert 'price' not in original['offers'][0]
        public_repeat = resolve(db, token_for(row))
        public_text = json.dumps(public_repeat, ensure_ascii=False)
        for letter in (customer_letter, sales_letter):
            public_text += str(letter(db, row))
        public_text += str(alert_letter(db, row, 'CRM_TIMEOUT'))
        assert 'chimmed' not in public_text and 'Химмед' not in public_text and 'stock_snapshot' not in public_text
    # A retry after availability changed still returns the first request and does not recapture.
    def unexpected_capture(*args):
        raise AssertionError('Availability must be captured only once')

    monkeypatch.setattr(service, 'capture_stock', unexpected_capture)
    again = submit(client, body, key=key)
    assert again.status_code == 200 and again.json() == first.json()
    with sessions() as db:
        repeated, _ = payload(db, db.get(SiteRequest, first.json()['siteRequestId']))
        assert repeated['items'][0]['stock_snapshot'] == original


def test_legacy_delivery_body_omits_new_null_fields(client, sessions):
    response = submit(client, form())
    assert response.status_code == 201, response.text
    request_id = response.json()['siteRequestId']
    with sessions.begin() as db:
        item = db.scalar(select(SiteRequestItem).where(SiteRequestItem.request_id == request_id))
        # A row that existed before this release. Its retry must keep the F1 canonical hash unchanged.
        item.stock_snapshot = None
        item.site_packaging_id = None
    with sessions() as db:
        body, _ = payload(db, db.get(SiteRequest, request_id))
        assert 'stock_snapshot' not in body['items'][0]
        assert 'site_packaging_id' not in body['items'][0]
