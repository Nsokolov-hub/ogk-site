"""Building form submissions the way the storefront sends them."""

import base64
import json
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

URL = '/api/v1/public/requests'
PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def form(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        'kind': 'product_rfq', 'lang': 'ru', 'formType': 'rfq',
        'customer': {'name': 'Иван Петров', 'company': 'ООО «Пример-Фарма»', 'phone': '+79991234567',
                     'email': 'zakupki@example.ru', 'inn': '7707083893', 'city': 'Москва',
                     'comment': 'Нужна холодовая цепь', 'marketingConsent': False},
        'items': [{'siteProductId': 'p-1', 'brand': 'EDQM', 'catalogNumber': 'Y0001897', 'cas': '28721-07-5',
                   'name': 'Oxcarbazepine CRS', 'packaging': '100 mg', 'quantity': 2, 'unit': 'pack',
                   'analogue': 'allowed', 'customPackaging': False,
                   'pageUrl': 'https://www.ogk-chem.ru/product/edqm-y0001897-oxcarbazepine-crs/'}],
        'personalDataConsent': True,
        'antispam': {'website': '', 'elapsedMs': 45000},
        'pageUrl': 'https://www.ogk-chem.ru/rfq/',
        'desiredDate': '2026-11-20',
    }
    body.update(changes)
    return body


def attribution_cookie(first: dict[str, str], last: dict[str, str] | None = None) -> str:
    raw = json.dumps({'first': first, 'last': last or first}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def submit(client: TestClient, body: dict[str, Any], *, key: str | None = None,
           attachment: tuple[str, bytes, str] | None = None, cookies: dict[str, str] | None = None):
    client.cookies.clear()
    for name, value in (cookies or {}).items():
        client.cookies.set(name, value)
    files = {'attachment': attachment} if attachment else None
    return client.post(URL, data={'payload': json.dumps(body, ensure_ascii=False)}, files=files,
                       headers={'Idempotency-Key': key or str(uuid4())})
