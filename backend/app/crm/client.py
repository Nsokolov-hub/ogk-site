"""Delivery of a request to the CRM, flow F1 (my-crm-project docs/site-integration.md).

One call = one multipart POST signed with HMAC-SHA256 over `<timestamp>.<raw body>`; the Idempotency-Key is the
request's own id, so a repeat after a lost answer never creates a second record in the CRM.
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import as_utc
from app.requests import attachments
from app.requests.models import SiteRequest, SiteRequestAttachment, SiteRequestItem

PATH = '/api/v1/integrations/site/requests'
SUBSCRIBERS_PATH = '/api/v1/integrations/site/subscribers'
# A CRM answer that a repeat cannot change: the request content or the contract is wrong (a person must look).
PERMANENT = {400, 404, 409, 413, 415, 422}
# Configuration problems on either side: alert at once, but keep retrying — fixing the token or the address
# allow-list heals them without touching the request.
CONFIGURATION = {401, 403}


@dataclass
class Outcome:
    kind: Literal['delivered', 'retry', 'failed']
    status_code: int | None = None
    error_code: str | None = None
    crm_id: str | None = None
    crm_number: str | None = None
    # Alert right away instead of waiting for the 15-minute watchdog.
    alert_now: bool = False


def number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def payload(db: Session, row: SiteRequest) -> tuple[dict[str, Any], list[tuple[str, bytes, str]]]:
    """The F1 body and its files, in the order of `attachments`."""
    items = db.scalars(select(SiteRequestItem).where(SiteRequestItem.request_id == row.id)
                       .order_by(SiteRequestItem.position)).all()
    files = db.scalars(select(SiteRequestAttachment).where(SiteRequestAttachment.request_id == row.id)
                       .order_by(SiteRequestAttachment.created_at, SiteRequestAttachment.id)).all()
    body = {
        'site_request_id': row.id,
        'site_number': row.number,
        'kind': row.kind,
        'lang': row.lang,
        'form_type': row.form_type,
        'created_at': as_utc(row.created_at).isoformat().replace('+00:00', 'Z'),
        'page_url': row.page_url,
        'desired_date': row.desired_date.isoformat() if row.desired_date else None,
        'customer': {
            'name': row.customer_name, 'company': row.company, 'inn': row.inn, 'phone': row.phone,
            'email': row.email, 'city': row.city, 'comment': row.comment,
            'marketing_consent': row.marketing_consent,
        },
        'items': [{
            'site_product_id': item.site_product_id, 'crm_product_id': None, 'brand': item.brand,
            'catalog_number': item.catalog_number, 'cas': item.cas, 'name': item.name,
            'packaging': item.packaging, 'quantity': number(item.quantity), 'unit': item.unit,
            'analogue': item.analogue, 'custom_packaging': item.custom_packaging, 'comment': item.comment,
            'page_url': item.page_url,
        } for item in items],
        'service': row.service,
        'attachments': [{'file_name': file.file_name, 'sha256': file.sha256, 'size': file.size} for file in files],
        'attribution': row.attribution,
    }
    contents = [(file.file_name, attachments.read(file.storage_key, file.sha256), file.media_type) for file in files]
    return body, contents


def sign(secret: str, timestamp: str, body: bytes) -> str:
    return 'sha256=' + hmac.new(secret.encode(), timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()


def http_client() -> httpx.Client:
    """The HTTP client of the calls; tests replace it with one on a mock transport."""
    return httpx.Client(timeout=settings.crm_timeout_seconds)


def deliver(db: Session, row: SiteRequest) -> Outcome:
    body, files = payload(db, row)
    request = httpx.Request('POST', settings.crm_url.rstrip('/') + PATH,
                            data={'payload': json.dumps(body, ensure_ascii=False)},
                            files=[('files', file) for file in files] or None)
    raw = request.read()
    stamp = str(int(time.time()))
    headers = {
        'Content-Type': request.headers['Content-Type'],
        'Authorization': f'Bearer {settings.crm_token}',
        'X-Site-Timestamp': stamp,
        'X-Site-Signature': sign(settings.crm_signing_secret, stamp, raw),
        'Idempotency-Key': row.id,
    }
    try:
        with http_client() as client:
            response = client.post(settings.crm_url.rstrip('/') + PATH, content=raw, headers=headers)
    except httpx.TimeoutException:
        return Outcome('retry', error_code='CRM_TIMEOUT')
    except httpx.HTTPError:
        return Outcome('retry', error_code='CRM_UNREACHABLE')
    code = response.status_code
    try:
        answer = response.json()
    except ValueError:
        answer = {}
    error = answer.get('code') if isinstance(answer, dict) and isinstance(answer.get('code'), str) else None
    if code in (200, 201) and isinstance(answer, dict) and answer.get('id'):
        return Outcome('delivered', code, crm_id=str(answer['id']), crm_number=str(answer.get('number') or ''))
    if code in PERMANENT:
        return Outcome('failed', code, (error or f'CRM_HTTP_{code}')[:80], alert_now=True)
    if code in CONFIGURATION:
        return Outcome('retry', code, (error or f'CRM_HTTP_{code}')[:80], alert_now=True)
    return Outcome('retry', code, (error or f'CRM_HTTP_{code}')[:80])


def post_json(path: str, body: dict[str, Any], idempotency_key: str) -> Outcome:
    """A signed JSON call to the integration module of the CRM (subscribers; the signature is the one of F1)."""
    raw = json.dumps(body, ensure_ascii=False).encode()
    stamp = str(int(time.time()))
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {settings.crm_token}',
               'X-Site-Timestamp': stamp, 'X-Site-Signature': sign(settings.crm_signing_secret, stamp, raw),
               'Idempotency-Key': idempotency_key}
    try:
        with http_client() as client:
            response = client.post(settings.crm_url.rstrip('/') + path, content=raw, headers=headers)
    except httpx.TimeoutException:
        return Outcome('retry', error_code='CRM_TIMEOUT')
    except httpx.HTTPError:
        return Outcome('retry', error_code='CRM_UNREACHABLE')
    code = response.status_code
    if code in (200, 201):
        return Outcome('delivered', code)
    # 404: a CRM that does not know the endpoint yet; it is retried until the CRM is updated.
    if code in PERMANENT - {404}:
        return Outcome('failed', code, f'CRM_HTTP_{code}')
    return Outcome('retry', code, f'CRM_HTTP_{code}')
