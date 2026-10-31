"""Accepting a request: validate, number, save with its attachments and queue its work in one transaction.

The customer gets an answer only after the commit (NFR-03). Delivery to the CRM and the letters happen later in
the worker, so an unavailable CRM or mail server never loses a request or slows the form down.
"""

import hashlib
import json
import secrets
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import DomainError
from app.outbox.models import OutboxEvent
from app.requests import antispam, attachments, attribution, contacts
from app.requests.models import NumberCounter, SiteRequest, SiteRequestAttachment, SiteRequestItem
from app.requests.schemas import RequestIn


class FormError(Exception):
    """Validation errors of the payload, by field path in the form's own (camelCase) names."""

    def __init__(self, fields: list[dict[str, str]]):
        self.fields = fields
        super().__init__('form invalid')


def advisory(db: Session, key: str) -> None:
    if db.bind is not None and db.bind.dialect.name == 'postgresql':
        number = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big', signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': number})


def next_number(db: Session, now: datetime) -> str:
    """S-123: one counter for all years, never reused (the number is shown to the customer).

    Business remark of 31 October 2026: «S-2026-000001» was too long, with too many zeros. The counter starts after
    the requests numbered the old way, so the numbers keep growing.
    """
    key = 'site_requests'
    advisory(db, f'number:{key}')
    counter = db.scalar(select(NumberCounter).where(NumberCounter.key == key).with_for_update()
                        .execution_options(populate_existing=True))
    if counter is None:
        counter = NumberCounter(key=key, value=db.scalar(select(func.count(SiteRequest.id))) or 0)
        db.add(counter)
    counter.value += 1
    db.flush()
    return f'S-{counter.value}'


def parse(payload: str | None) -> tuple[RequestIn, str]:
    if not payload:
        raise DomainError('PAYLOAD_REQUIRED', 'Передайте данные формы в части payload', 422, 'payload')
    try:
        raw = json.loads(payload)
    except ValueError:
        raise DomainError('PAYLOAD_INVALID', 'Данные формы должны быть в формате JSON', 422, 'payload') from None
    try:
        data = RequestIn.model_validate(raw)
    except ValidationError as exc:
        raise FormError([{'field': '.'.join(str(part) for part in error['loc']) or 'payload',
                          'message': error['msg']}
                         for error in exc.errors(include_url=False, include_context=False)]) from None
    if not isinstance(raw, dict):
        raise DomainError('PAYLOAD_INVALID', 'Данные формы должны быть объектом JSON', 422, 'payload')
    # The trap field and the timing differ between two clicks of one submission; the content does not.
    content = {key: value for key, value in raw.items() if key not in ('antispam', 'captchaToken')}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return data, digest


def result(row: SiteRequest) -> dict[str, Any]:
    return {'site_request_id': row.id, 'number': row.number}


def queue(db: Session, row: SiteRequest) -> None:
    now = utcnow()
    db.add(OutboxEvent(event_key=f'crm-deliver:{row.id}', kind='crm.deliver',
                       payload={'request_id': row.id, 'window_start': now.isoformat()}))
    db.add(OutboxEvent(event_key=f'mail-customer:{row.id}', kind='mail.customer', payload={'request_id': row.id}))
    db.add(OutboxEvent(event_key=f'mail-sales:{row.id}', kind='mail.sales', payload={'request_id': row.id}))


def accept(db: Session, payload: str | None, client_key: str | None, upload: tuple[str, bytes] | None,
           ip: str | None, user_agent: str | None, cookies: dict[str, str]) -> tuple[dict[str, Any], bool]:
    """Save the request once per browser key; (answer, created)."""
    if not client_key or not 8 <= len(client_key) <= 64:
        raise DomainError('IDEMPOTENCY_KEY_REQUIRED', 'Передайте заголовок Idempotency-Key', 422, 'Idempotency-Key')
    data, digest = parse(payload)
    if data.antispam.website:
        # A filled trap field: a bot. It gets an ordinary-looking answer and nothing is saved.
        now = utcnow()
        return {'site_request_id': str(uuid4()), 'number': f'S-{secrets.randbelow(9000) + 100}'}, True
    advisory(db, f'site-request:{client_key}')
    previous = db.scalar(select(SiteRequest).where(SiteRequest.client_key == client_key))
    if previous is not None:
        if previous.payload_hash != digest:
            raise DomainError('IDEMPOTENCY_CONFLICT', 'Этот ключ уже использован для другой заявки', 409)
        return result(previous), False
    file = attachments.validate(*upload) if upload else None
    if settings.check_email_domains and contacts.domain_receives_mail(data.customer.email.rsplit('@', 1)[1].lower()) \
            is False:
        raise DomainError('EMAIL_DOMAIN', 'Почтовый домен в адресе e-mail не найден: проверьте часть после @', 422,
                          'customer.email')
    suspicious = antispam.check(db, data, ip)
    now = utcnow()
    customer = data.customer
    row = SiteRequest(
        number=next_number(db, now), client_key=client_key, payload_hash=digest, kind=data.kind, lang=data.lang,
        form_type=data.form_type, page_url=data.page_url, customer_name=customer.name, company=customer.company,
        inn=customer.inn, phone=customer.phone, email=customer.email, city=customer.city, comment=customer.comment,
        desired_date=data.desired_date, marketing_consent=customer.marketing_consent, consent_at=now,
        client_ip=ip, user_agent=(user_agent or '')[:500] or None,
        service=data.service.model_dump() if data.service else None,
        attribution=attribution.collect(cookies, data.page_url), suspicious=suspicious,
    )
    db.add(row)
    db.flush()
    for position, item in enumerate(data.items, start=1):
        db.add(SiteRequestItem(request_id=row.id, position=position, **item.model_dump()))
    if file and upload:
        key, checksum = attachments.store(upload[1])
        db.add(SiteRequestAttachment(request_id=row.id, file_name=file[0], media_type=file[1], size=len(upload[1]),
                                     sha256=checksum, storage_key=key))
    queue(db, row)
    db.flush()
    return result(row), True
