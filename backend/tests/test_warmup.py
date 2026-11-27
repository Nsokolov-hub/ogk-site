import io
import json
from urllib.error import HTTPError

import pytest

from app.core import warmup


def test_deploy_warmup_reads_live_api_and_actual_product_identifiers(monkeypatch):
    calls = []

    def get(url, timeout):
        calls.append(url)
        result = {'items': [{'slug': 'example-product', 'catalogNumber': 'A/B 1', 'cas': '67-56-1'}]} \
            if '/catalog/popular?' in url else {}
        return io.BytesIO(json.dumps(result).encode())

    monkeypatch.setattr(warmup, 'urlopen', get)
    checked = warmup.warm()
    assert len(checked) == 8
    assert all(url.startswith('http://127.0.0.1:8000/') for url in calls)
    assert calls[0].endswith('/ready')
    assert calls[-2].endswith('/search?q=A%2FB+1&lang=ru')
    assert calls[-1].endswith('/cas/67-56-1')


def test_unhealthy_endpoint_fails_warmup_before_web_can_be_replaced(monkeypatch):
    calls = []

    def unavailable(url, timeout):
        calls.append(url)
        raise HTTPError(url, 503, 'overloaded', {}, None)

    monkeypatch.setattr(warmup, 'urlopen', unavailable)
    with pytest.raises(HTTPError):
        warmup.warm()
    assert calls == ['http://127.0.0.1:8000/ready']
