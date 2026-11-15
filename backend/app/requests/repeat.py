"""An expiring receipt link restores the item list only, with no contacts, files or original request number."""

import base64
import binascii
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import as_utc, utcnow
from app.core.errors import DomainError
from app.requests.models import SiteRequest, SiteRequestItem

LIFETIME = timedelta(days=90)
PURPOSE = b'ogk-repeat-items-v1.'


def encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def signature(payload: str) -> str:
    return encode(hmac.new(settings.secret_key.encode(), PURPOSE + payload.encode(), hashlib.sha256).digest())


def token_for(row: SiteRequest) -> str:
    expires = int((as_utc(row.created_at) + LIFETIME).timestamp())
    payload = encode(json.dumps({'v': 1, 'id': row.id, 'exp': expires}, separators=(',', ':')).encode())
    return f'{payload}.{signature(payload)}'


def repeat_url(row: SiteRequest) -> str:
    prefix = '/en' if row.lang == 'en' else ''
    # Fragments are not sent to the server or in Referer. The storefront posts the token in a body and clears it.
    return f'{settings.site_url.rstrip("/")}{prefix}/rfq/#repeat={token_for(row)}'


def resolve(db: Session, token: str, *, now: datetime | None = None) -> dict[str, Any]:
    invalid = DomainError('REPEAT_UNAVAILABLE', 'Ссылка недоступна или срок её действия истёк. '
                          'Добавьте товары в новый запрос.', 404)
    if not 40 <= len(token) <= 500:
        raise invalid
    try:
        payload, proof = token.split('.')
        if not hmac.compare_digest(proof, signature(payload)):
            raise ValueError('signature')
        data = json.loads(decode(payload))
        if not isinstance(data, dict) or set(data) != {'id', 'v', 'exp'} or data['v'] != 1:
            raise ValueError('purpose')
        request_id = str(UUID(data['id']))
        stamp = int(as_utc(now or utcnow()).timestamp())
        if type(data['exp']) is not int or not stamp < data['exp'] <= stamp + int(LIFETIME.total_seconds()) + 60:
            raise ValueError('expiry')
    except (ValueError, TypeError, KeyError, binascii.Error, UnicodeDecodeError):
        raise invalid from None
    row = db.get(SiteRequest, request_id)
    if row is None or data['exp'] != int((as_utc(row.created_at) + LIFETIME).timestamp()):
        raise invalid
    items = db.scalars(select(SiteRequestItem).where(SiteRequestItem.request_id == row.id)
                       .order_by(SiteRequestItem.position)).all()
    if not items:
        raise invalid
    return {
        'items': [{
            'name': item.name, 'brand': item.brand, 'catalog_number': item.catalog_number, 'cas': item.cas,
            'packaging': item.packaging, 'quantity': float(item.quantity), 'unit': item.unit,
            'analogue': item.analogue, 'custom_packaging': item.custom_packaging,
        } for item in items],
        'expires_at': datetime.fromtimestamp(data['exp'], tz=as_utc(row.created_at).tzinfo).isoformat(),
    }
