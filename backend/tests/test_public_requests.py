"""The forms' endpoint: a request is saved with its work queued before the customer gets an answer."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.db import utcnow
from app.outbox.models import OutboxEvent
from app.requests import antispam
from app.requests.models import RateEvent, SiteRequest, SiteRequestAttachment, SiteRequestItem
from tests.support import PDF, attribution_cookie, form, submit


def test_request_is_saved_numbered_and_queued(client, sessions):
    response = submit(client, form(), cookies={
        'ogk_attr': attribution_cookie({'landing_url': 'https://www.ogk-chem.ru/articles/edqm-vs-usp/',
                                        'referrer': 'https://ya.ru/', 'at': '2026-10-15T10:22:11Z'},
                                       {'landing_url': 'https://www.ogk-chem.ru/catalog/reference-standards/edqm/',
                                        'utm_source': 'yandex', 'utm_medium': 'cpc', 'yclid': '42'}),
        '_ym_uid': '1700000000123', '_ga': 'GA1.1.123456789.1700000000'})
    assert response.status_code == 201, response.text
    answer = response.json()
    assert answer['number'] == f'S-{utcnow().year}-000001'
    with sessions() as db:
        row = db.get(SiteRequest, answer['siteRequestId'])
        assert (row.status, row.company, row.inn, str(row.desired_date)) == (
            'accepted', 'ООО «Пример-Фарма»', '7707083893', '2026-11-20')
        item = db.scalar(select(SiteRequestItem).where(SiteRequestItem.request_id == row.id))
        assert (item.catalog_number, item.analogue, item.packaging) == ('Y0001897', 'allowed', '100 mg')
        assert row.attribution['channel'] == 'cpc'
        assert row.attribution['first_touch']['referrer'] == 'https://ya.ru/'
        assert row.attribution['client_ids'] == {'ym_uid': '1700000000123', 'ga_client_id': '123456789.1700000000'}
        kinds = sorted(event.kind for event in db.scalars(select(OutboxEvent)))
        assert kinds == ['crm.deliver', 'mail.customer', 'mail.sales']


def test_numbers_follow_each_other(client):
    first = submit(client, form()).json()['number']
    second = submit(client, form()).json()['number']
    assert int(second[-6:]) == int(first[-6:]) + 1


def test_double_click_returns_the_same_request(client, sessions):
    key = str(uuid4())
    first = submit(client, form(), key=key)
    again = submit(client, form(antispam={'website': '', 'elapsedMs': 46000}), key=key)
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json() == first.json()
    with sessions() as db:
        assert len(db.scalars(select(SiteRequest)).all()) == 1


def test_key_reused_for_another_request_is_a_conflict(client):
    key = str(uuid4())
    submit(client, form(), key=key)
    response = submit(client, form(customer={**form()['customer'], 'company': 'ООО «Другая»'}), key=key)
    assert response.status_code == 409


@pytest.mark.parametrize('change, field', [
    ({'customer': {**form()['customer'], 'phone': '+7999123'}}, 'customer.phone'),
    ({'customer': {**form()['customer'], 'inn': '7707083890'}}, 'customer.inn'),
    ({'customer': {**form()['customer'], 'email': 'zakupki@example'}}, 'customer.email'),
    ({'personalDataConsent': False}, 'personalDataConsent'),
    ({'items': []}, ''),
])
def test_invalid_fields_are_named(client, change, field):
    response = submit(client, form(**change))
    assert response.status_code == 422, response.text
    body = response.json()
    assert body['code'] == 'VALIDATION_ERROR'
    assert any(item['field'] == field or (not field and item['field'] in ('', 'payload'))
               for item in body['fields']), body


def test_one_click_takes_one_line(client):
    body = form(kind='one_click', formType='one_click')
    body['items'] = body['items'] * 2
    assert submit(client, body).status_code == 422


def test_service_request_needs_its_form(client):
    assert submit(client, form(kind='service', items=[])).status_code == 422
    response = submit(client, form(kind='service', items=[], service={
        'slug': 'cold-chain', 'name': 'Холодовая цепь', 'fields': {'Откуда': 'Германия', 'Режим': '+2…+8 °C'}}))
    assert response.status_code == 201, response.text


def test_trap_field_answers_like_success_and_saves_nothing(client, sessions):
    response = submit(client, form(antispam={'website': 'http://spam.example', 'elapsedMs': 900}))
    assert response.status_code == 201
    with sessions() as db:
        assert not db.scalars(select(SiteRequest)).all()


def test_attachment_is_kept_with_its_checksum(client, sessions):
    response = submit(client, form(), attachment=('spec.pdf', PDF, 'application/pdf'))
    assert response.status_code == 201, response.text
    with sessions() as db:
        file = db.scalar(select(SiteRequestAttachment))
        assert (file.file_name, file.size, file.media_type) == ('spec.pdf', len(PDF), 'application/pdf')
        assert (settings.storage_dir / file.storage_key).read_bytes() == PDF


@pytest.mark.parametrize('attachment, code', [
    (('virus.exe', b'MZ\x90\x00', 'application/octet-stream'), 'FILE_TYPE'),
    (('fake.pdf', b'<html><script>', 'application/pdf'), 'FILE_CONTENT'),
])
def test_unsafe_attachments_are_refused(client, sessions, attachment, code):
    response = submit(client, form(), attachment=attachment)
    assert response.status_code == 422 and response.json()['code'] == code
    with sessions() as db:
        assert not db.scalars(select(SiteRequest)).all()


def test_attachment_over_ten_megabytes_is_refused(client, monkeypatch):
    monkeypatch.setattr(settings, 'max_attachment_bytes', len(PDF) - 1)
    response = submit(client, form(), attachment=('spec.pdf', PDF, 'application/pdf'))
    assert response.status_code == 413


def test_too_fast_filling_is_only_marked_without_a_captcha_key(client, sessions):
    response = submit(client, form(antispam={'website': '', 'elapsedMs': 800}))
    assert response.status_code == 201
    with sessions() as db:
        assert db.get(SiteRequest, response.json()['siteRequestId']).suspicious is True


def test_too_fast_filling_asks_for_a_captcha(client, monkeypatch):
    monkeypatch.setattr(settings, 'smartcaptcha_server_key', 'server-key')
    monkeypatch.setattr(antispam, 'captcha_valid', lambda token, ip: token == 'good-token')
    fast = form(antispam={'website': '', 'elapsedMs': 800})
    response = submit(client, fast)
    assert response.status_code == 428 and response.json()['code'] == 'CAPTCHA_REQUIRED'
    assert submit(client, {**fast, 'captchaToken': 'bad-token'}).status_code == 428
    assert submit(client, {**fast, 'captchaToken': 'good-token'}).status_code == 201


def test_address_over_the_hard_limit_is_refused(client, sessions, monkeypatch):
    monkeypatch.setattr(settings, 'rate_hard_limit', 3)
    monkeypatch.setattr(settings, 'rate_soft_limit', 100)
    for _ in range(3):
        assert submit(client, form()).status_code == 201
    response = submit(client, form())
    assert response.status_code == 429 and response.json()['code'] == 'RATE_LIMITED'


def test_old_rate_events_are_pruned(sessions):
    with sessions.begin() as db:
        db.add(RateEvent(key='k', created_at=utcnow() - timedelta(days=2)))
        db.add(RateEvent(key='k'))
    with sessions.begin() as db:
        assert antispam.prune(db) == 1


def test_key_is_required(client):
    response = client.post('/api/v1/public/requests', data={'payload': '{}'})
    assert response.status_code == 422 and response.json()['code'] == 'IDEMPOTENCY_KEY_REQUIRED'
