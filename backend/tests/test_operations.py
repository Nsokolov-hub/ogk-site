"""Subscriptions (TZ 11.2, NFR-07), shared search limits (NFR-05), the watchdog and error reports (TZ 12.1)."""

import hashlib
import hmac
import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select

from app.catalog import routes
from app.core import monitoring, ratelimit, storefront
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import DomainError
from app.crm import client as crm
from app.notifications import mail
from app.outbox import worker
from app.outbox.models import OutboxEvent
from app.subscriptions.models import Subscriber
from app.subscriptions.service import export_csv

SUBSCRIBE = {'email': 'Zakupki@Example.ru', 'personalDataConsent': True, 'marketingConsent': True, 'lang': 'ru',
             'source': 'home', 'pageUrl': 'https://www.ogk-chem.ru/', 'website': ''}


def kinds(sessions) -> list[str]:
    with sessions() as db:
        return sorted(event.kind for event in db.scalars(select(OutboxEvent)))


def test_subscription_is_saved_with_both_consents_and_queued(client, sessions):
    response = client.post('/api/v1/public/subscriptions/', json=SUBSCRIBE)
    assert response.status_code == 200 and response.json() == {'ok': True}
    with sessions() as db:
        row = db.scalar(select(Subscriber))
        assert (row.email, row.status, row.lang, row.source) == ('zakupki@example.ru', 'active', 'ru', 'home')
        assert row.personal_data_consent_at and row.marketing_consent_at and len(row.unsubscribe_token) >= 32
    assert kinds(sessions) == ['crm.subscriber', 'mail.subscriber', 'mail.subscriber_sales']
    # The same address again: the same answer, no second letter.
    assert client.post('/api/v1/public/subscriptions', json=SUBSCRIBE).json() == {'ok': True}
    assert len(kinds(sessions)) == 3


def test_subscription_needs_both_consents_and_a_valid_address(client):
    for change in ({'marketingConsent': False}, {'personalDataConsent': False}, {'email': 'not-an-address'}):
        assert client.post('/api/v1/public/subscriptions', json={**SUBSCRIBE, **change}).status_code == 422


def test_trap_field_saves_nothing_and_limits_stop_floods(client, sessions):
    assert client.post('/api/v1/public/subscriptions', json={**SUBSCRIBE, 'website': 'x'}).status_code == 200
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Subscriber)) == 0
    codes = [client.post('/api/v1/public/subscriptions', json={**SUBSCRIBE, 'email': f'a{i}@example.ru'}).status_code
             for i in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429


def test_unsubscribe_by_token_and_subscribe_again(client, sessions):
    client.post('/api/v1/public/subscriptions', json=SUBSCRIBE)
    with sessions() as db:
        token = db.scalar(select(Subscriber.unsubscribe_token))
    assert client.post('/api/v1/public/subscriptions/unsubscribe', json={'token': 'x' * 32}).json() == {'ok': True}
    assert client.post('/api/v1/public/subscriptions/unsubscribe/', json={'token': token}).status_code == 200
    with sessions() as db:
        row = db.scalar(select(Subscriber))
        assert row.status == 'unsubscribed' and row.unsubscribed_at is not None
        assert export_csv(db).count('\n') == 1 and 'zakupki@example.ru' in export_csv(db, None)
    assert kinds(sessions).count('crm.subscriber') == 2
    client.post('/api/v1/public/subscriptions', json=SUBSCRIBE)
    with sessions() as db:
        assert db.scalar(select(Subscriber.status)) == 'active'
    assert kinds(sessions).count('mail.subscriber') == 2


def test_worker_sends_the_welcome_letter_and_the_crm_copy(client, sessions, monkeypatch):
    client.post('/api/v1/public/subscriptions', json=SUBSCRIBE)
    letters: list[dict] = []
    monkeypatch.setattr(mail, 'send', lambda to, subject, body, **kw: letters.append(
        {'to': to, 'subject': subject, 'body': body, **kw}))
    calls: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(404 if len(calls) == 1 else 201, json={})

    monkeypatch.setattr(crm, 'http_client', lambda: httpx.Client(transport=httpx.MockTransport(answer)))
    with sessions.begin() as db:
        counts = worker.process_events(db)
    assert counts == {'succeeded': 2, 'retried': 1, 'failed': 0}
    welcome = next(letter for letter in letters if letter['to'] == ['zakupki@example.ru'])
    assert '/unsubscribe/?t=' in welcome['body'] and welcome['headers']['List-Unsubscribe'].startswith('<https://')
    assert any(letter['to'] == [settings.sales_email] for letter in letters)
    # The CRM did not know the endpoint yet (404): retried, then delivered.
    request = calls[0]
    body = request.content
    stamp = request.headers['X-Site-Timestamp']
    expected = 'sha256=' + hmac.new(b'test-signing-secret', stamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
    assert request.url.path == '/api/v1/integrations/site/subscribers' and request.headers['X-Site-Signature'] == expected
    assert json.loads(body)['subscribed'] is True
    with sessions.begin() as db:
        assert worker.process_events(db, now=utcnow() + timedelta(minutes=5))['succeeded'] == 1
    with sessions() as db:
        assert db.scalar(select(Subscriber.crm_synced_at)) is not None


def test_crm_copies_wait_while_delivery_is_off(client, sessions, monkeypatch):
    monkeypatch.setattr(settings, 'crm_delivery_enabled', False)
    monkeypatch.setattr(mail, 'send', lambda *a, **kw: None)
    client.post('/api/v1/public/subscriptions', json=SUBSCRIBE)
    with sessions.begin() as db:
        assert worker.process_events(db)['succeeded'] == 2
    with sessions() as db:
        assert db.scalar(select(OutboxEvent.status).where(OutboxEvent.kind == 'crm.subscriber')) == 'pending'


class FakeRequest:
    def __init__(self, host: str, headers: dict[str, str] | None = None):
        self.client = type('Client', (), {'host': host})()
        self.headers = headers or {}


def test_search_limit_counts_visitors_and_skips_the_storefronts_cached_requests(monkeypatch):
    monkeypatch.setattr(settings, 'redis_url', '')
    monkeypatch.setattr(settings, 'search_rate_per_minute', 2)
    monkeypatch.setattr(settings, 'revalidate_secret', 'shared-secret')
    monkeypatch.setattr(routes, 'limiter', ratelimit.RateLimiter('search-test'))
    for _ in range(2):
        routes.limited(FakeRequest('10.0.0.1'))  # type: ignore[arg-type]
    with pytest.raises(DomainError) as refused:
        routes.limited(FakeRequest('10.0.0.1'))  # type: ignore[arg-type]
    assert refused.value.status == 429
    routes.limited(FakeRequest('10.0.0.2'))  # type: ignore[arg-type]
    for _ in range(5):
        routes.limited(FakeRequest('172.18.0.5', {'x-site-token': 'shared-secret'}))  # type: ignore[arg-type]
    with pytest.raises(DomainError):
        for _ in range(3):
            routes.limited(FakeRequest('172.18.0.5', {'x-site-token': 'wrong'}))  # type: ignore[arg-type]


def test_limits_fall_back_to_the_process_when_redis_is_down(monkeypatch):
    class Broken:
        def pipeline(self):
            raise ConnectionError('down')

    monkeypatch.setattr(ratelimit, 'redis_client', lambda: Broken())
    limiter = ratelimit.RateLimiter('fallback')
    assert [limiter.allow('a', 1), limiter.allow('a', 1)] == [True, False]


def test_storefront_cache_is_dropped_with_the_shared_secret(monkeypatch):
    calls: list[dict] = []

    def post(url: str, **kw: object) -> httpx.Response:
        calls.append({'url': url, **kw})
        return httpx.Response(200)

    monkeypatch.setattr(storefront.httpx, 'post', post)
    monkeypatch.setattr(settings, 'web_url', '')
    assert storefront.revalidate_catalog() is False
    monkeypatch.setattr(settings, 'web_url', 'http://web:3000')
    monkeypatch.setattr(settings, 'revalidate_secret', 'secret')
    assert storefront.revalidate_catalog() is True
    assert calls == [{'url': 'http://web:3000/api/revalidate/', 'timeout': 5.0,
                      'headers': {'X-Revalidate-Secret': 'secret'}, 'json': {'tags': ['catalog']}}]


def test_watchdog_alerts_once_an_hour_per_problem(sessions, monkeypatch):
    monkeypatch.setattr(monitoring, 'check_parts', lambda db: {'database': True, 'search': False})
    with sessions.begin() as db:
        db.add(OutboxEvent(event_key='old', kind='mail.customer', payload={}, created_at=utcnow() - timedelta(hours=1)))
    sent: list[str] = []
    dog = monitoring.Watchdog()
    with sessions() as db:
        assert sorted(dog.run(db, sent.append)) == ['queue', 'search']
        assert dog.run(db, sent.append) == []
    assert len(sent) == 2 and 'поиск' in ' '.join(sent)
    dog.alerted = {key: value - timedelta(hours=2) for key, value in dog.alerted.items()}
    with sessions() as db:
        assert len(dog.run(db, sent.append)) == 2


def test_error_reports_carry_no_personal_data():
    report = {'request': {'url': 'https://www.ogk-chem.ru/api/v1/public/requests', 'data': '{"phone": "+7999"}',
                          'cookies': {'ogk_attr': 'x'}, 'headers': {'User-Agent': 'UA', 'Cookie': 'a=b',
                                                                   'X-Forwarded-For': '1.2.3.4'}},
              'user': {'ip_address': '1.2.3.4'}}
    cleaned = monitoring.scrub(report, {})
    assert cleaned['request'] == {'url': 'https://www.ogk-chem.ru/api/v1/public/requests', 'headers': {'User-Agent': 'UA'}}
    assert 'user' not in cleaned


def test_health_for_the_uptime_monitor(client, monkeypatch):
    monkeypatch.setattr('app.main.check_parts', lambda db: {'database': True, 'search': True})
    assert client.get('/api/v1/health').json() == {'status': 'ok', 'database': True, 'search': True}
    monkeypatch.setattr('app.main.check_parts', lambda db: {'database': True, 'search': False})
    assert client.get('/api/v1/health').status_code == 503
