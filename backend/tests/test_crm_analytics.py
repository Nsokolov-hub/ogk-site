"""The CRM asks the site for the Yandex reports with the signature of its events; the token goes one way only."""

import hashlib
import hmac
import json
import time

import pytest
from sqlalchemy import select

from app.admin.models import AuditEntry
from app.analytics import yandex
from app.catalog.settings import get_setting
from app.core.config import settings
from tests.admin.test_analytics import TOKEN, fake  # noqa: F401 — the fixture of Yandex's answers

SECRET = 'crm-events-secret'
URL = '/api/v1/crm/analytics'


@pytest.fixture(autouse=True)
def link_on(monkeypatch):
    monkeypatch.setattr(settings, 'crm_events_secret', SECRET)
    monkeypatch.setattr(settings, 'crm_events_allowed_ips', '')


def ask(client, body: dict, *, secret: str = SECRET, stamp: int | None = None):
    raw = json.dumps(body, ensure_ascii=False).encode()
    moment = str(stamp if stamp is not None else int(time.time()))
    signature = 'sha256=' + hmac.new(secret.encode(), moment.encode() + b'.' + raw, hashlib.sha256).hexdigest()
    return client.post(URL, content=raw, headers={'Content-Type': 'application/json', 'X-CRM-Timestamp': moment,
                                                  'X-CRM-Signature': signature})


def test_only_the_signed_crm_gets_the_reports(client, fake):  # noqa: F811
    assert ask(client, {'action': 'report'}, secret='wrong').status_code == 401
    assert ask(client, {'action': 'report'}, stamp=int(time.time()) - 3600).json()['code'] == 'CRM_SIGNATURE_EXPIRED'
    assert ask(client, {'action': 'drop tables'}).json()['code'] == 'CRM_REQUEST_INVALID'
    empty = ask(client, {'action': 'report', 'period': 7}).json()
    assert empty['status']['connected'] is False and empty['metrika'] is None
    assert ask(client, {'action': 'report', 'period': 5}).json()['code'] == 'PERIOD_INVALID'
    assert not fake.calls


def test_the_crm_connects_the_token_and_reads_the_reports(client, fake, sessions):  # noqa: F811
    assert ask(client, {'action': 'connect', 'author': 'Анна'}).json()['code'] == 'TOKEN_INVALID'
    connected = ask(client, {'action': 'connect', 'token': TOKEN, 'author': 'Анна Петрова'})
    assert connected.status_code == 200, connected.text
    answer = connected.json()
    assert TOKEN not in connected.text and answer['status']['tail'] == TOKEN[-4:]
    assert answer['status']['savedBy'] == 'Анна Петрова (CRM)' and answer['access']['webmaster']['ok']
    assert len([g for g in answer['goals'] if g['state'] == 'created']) == len(yandex.GOALS) - 1

    report = ask(client, {'action': 'refresh', 'period': 7}).json()
    assert report['metrika']['totals']['visits'] == 20 and report['webmaster']['summary']['inSearch'] == 9
    assert ask(client, {'action': 'sitemap', 'author': 'Анна Петрова'}).json()['state'] == 'added'
    assert {g['state'] for g in ask(client, {'action': 'goals'}).json()['goals']} == {'exists'}

    with sessions() as db:
        assert yandex.token(db) == TOKEN
        names = {(e.actor_name, e.entity_id) for e in db.scalars(select(AuditEntry))}
        assert ('Анна Петрова (CRM)', 'yandex_token') in names and ('Анна Петрова (CRM)', 'webmaster_sitemap') in names
    assert ask(client, {'action': 'disconnect', 'author': 'Анна Петрова'}).json()['status']['connected'] is False
    with sessions() as db:
        assert get_setting(db, 'yandex_token') is None
