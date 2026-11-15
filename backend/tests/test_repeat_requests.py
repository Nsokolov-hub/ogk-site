"""A receipt can restore an editable list, without disclosing the customer's other information."""

from datetime import timedelta
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.db import utcnow
from app.core.errors import DomainError
from app.outbox.models import OutboxEvent
from app.requests.models import SiteRequest
from app.requests.repeat import repeat_url, resolve, token_for
from tests.support import form, submit

URL = '/api/v1/public/requests/repeat/resolve'


def receipt(client, sessions):
    body = form(items=[{**form()['items'][0], 'quantity': 9, 'packaging': '1 ampoule',
                       'catalogNumber': '1235831-1AMP', 'analogue': 'requested', 'customPackaging': True}])
    created = submit(client, body).json()['siteRequestId']
    with sessions() as db:
        link = repeat_url(db.get(SiteRequest, created))
    assert not urlsplit(link).query
    return created, urlsplit(link).fragment.removeprefix('repeat=')


def test_repeat_restores_only_items_without_writes(client, sessions):
    created, token = receipt(client, sessions)
    with sessions() as db:
        before = len(db.scalars(select(OutboxEvent)).all())
    response = client.post(URL, json={'token': token})
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'private, no-store'
    body = response.json()
    assert set(body) == {'items', 'expiresAt'}
    item = body['items'][0]
    assert (item['quantity'], item['packaging'], item['catalogNumber'], item['analogue'],
            item['customPackaging']) == (9, '1 ampoule', '1235831-1AMP', 'requested', True)
    assert set(item) == {'name', 'brand', 'catalogNumber', 'cas', 'packaging', 'quantity', 'unit',
                         'analogue', 'customPackaging'}
    assert created not in response.text and 'example.ru' not in response.text
    with sessions() as db:
        assert len(db.scalars(select(SiteRequest)).all()) == 1
        assert len(db.scalars(select(OutboxEvent)).all()) == before


def test_repeat_tampering_expiry_and_missing_request_are_indistinguishable(client, sessions):
    created, token = receipt(client, sessions)
    corrupted = token[:-1] + ('a' if token[-1] != 'a' else 'b')
    bad = client.post(URL, json={'token': corrupted})
    assert bad.status_code == 404
    with sessions() as db:
        with pytest.raises(DomainError) as expired:
            resolve(db, token, now=utcnow() + timedelta(days=91))
        assert expired.value.code == bad.json()['code'] == 'REPEAT_UNAVAILABLE'
    missing_token = token_for(SiteRequest(id=str(uuid4()), created_at=utcnow()))
    missing = client.post(URL, json={'token': missing_token})
    assert missing.status_code == 404
    assert {k: v for k, v in missing.json().items() if k != 'requestId'} == {
        k: v for k, v in bad.json().items() if k != 'requestId'}
