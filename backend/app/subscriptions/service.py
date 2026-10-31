"""Subscribe and unsubscribe (TZ 11.2, NFR-07). Both answers look the same whatever the address's past, so the
form never tells a stranger whether someone is subscribed."""

import csv
import hashlib
import io
import secrets
from datetime import timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import DomainError
from app.outbox.models import OutboxEvent
from app.requests.contacts import email_problem
from app.requests.models import RateEvent
from app.requests.schemas import EMAIL_RE
from app.subscriptions.models import Subscriber

HOURLY_LIMIT = 10


class SubscribeIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra='ignore',
                              str_strip_whitespace=True)
    email: str = Field(max_length=254)
    personal_data_consent: Literal[True]
    marketing_consent: Literal[True]
    lang: Literal['ru', 'en'] = 'ru'
    source: str = Field(default='home', max_length=40)
    page_url: str | None = Field(default=None, max_length=2000)
    # The trap field of the form: a person never fills it.
    website: str = Field(default='', max_length=200)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value: str) -> str:
        if not EMAIL_RE.match(value) or email_problem(value):
            raise ValueError('Неверный адрес почты')
        return value.lower()


class UnsubscribeIn(BaseModel):
    token: str = Field(min_length=16, max_length=64)


def limit(db: Session, ip: str | None) -> None:
    key = hashlib.sha256(f'site-subscribe:{ip or "unknown"}'.encode()).hexdigest()
    since = utcnow() - timedelta(hours=1)
    count = db.scalar(select(func.count()).select_from(RateEvent).where(RateEvent.key == key,
                                                                         RateEvent.created_at >= since)) or 0
    if count >= HOURLY_LIMIT:
        raise DomainError('RATE_LIMITED', 'Слишком много попыток с вашего адреса. Повторите позже', 429)
    db.add(RateEvent(key=key))


def queue(db: Session, row: Subscriber, *, welcome: bool) -> None:
    """The welcome letter with the unsubscribe link, a note to sales and the copy for the CRM."""
    stamp = f'{row.id}:{row.version}'
    if welcome:
        db.add(OutboxEvent(event_key=f'subscriber-welcome:{stamp}', kind='mail.subscriber',
                           payload={'subscriber_id': row.id}))
        db.add(OutboxEvent(event_key=f'subscriber-sales:{stamp}', kind='mail.subscriber_sales',
                           payload={'subscriber_id': row.id}))
    db.add(OutboxEvent(event_key=f'crm-subscriber:{stamp}', kind='crm.subscriber', payload={'subscriber_id': row.id}))


def subscribe(db: Session, data: SubscribeIn, ip: str | None, user_agent: str | None) -> None:
    if data.website:
        return
    limit(db, ip)
    now = utcnow()
    row = db.scalar(select(Subscriber).where(Subscriber.email == data.email).with_for_update())
    if row is not None and row.status == 'active':
        return
    if row is None:
        row = Subscriber(email=data.email, unsubscribe_token=secrets.token_urlsafe(32))
        db.add(row)
    else:
        row.version += 1
    row.status, row.lang, row.source, row.page_url = 'active', data.lang, data.source, data.page_url
    row.personal_data_consent_at = row.marketing_consent_at = now
    row.client_ip, row.user_agent, row.unsubscribed_at = ip, (user_agent or '')[:500] or None, None
    db.flush()
    queue(db, row, welcome=True)


def unsubscribe(db: Session, token: str) -> None:
    row = db.scalar(select(Subscriber).where(Subscriber.unsubscribe_token == token).with_for_update())
    if row is None or row.status == 'unsubscribed':
        return
    row.status, row.unsubscribed_at = 'unsubscribed', utcnow()
    row.version += 1
    db.flush()
    queue(db, row, welcome=False)


def export_csv(db: Session, status: str | None = 'active') -> str:
    """For a mailing service: address, language, status, consent date, source."""
    statement = select(Subscriber).order_by(Subscriber.created_at)
    if status:
        statement = statement.where(Subscriber.status == status)
    out = io.StringIO()
    writer = csv.writer(out, delimiter=';')
    writer.writerow(['email', 'lang', 'status', 'consent_at', 'source', 'unsubscribed_at'])
    for row in db.scalars(statement):
        writer.writerow([row.email, row.lang, row.status, row.marketing_consent_at.isoformat(), row.source or '',
                         row.unsubscribed_at.isoformat() if row.unsubscribed_at else ''])
    return '﻿' + out.getvalue()


def crm_payload(row: Subscriber) -> dict[str, Any]:
    # version: the CRM keeps the newest state when deliveries arrive out of order.
    return {'site_subscriber_id': row.id, 'version': row.version, 'email': row.email, 'lang': row.lang,
            'subscribed': row.status == 'active', 'consent_at': row.marketing_consent_at.isoformat(),
            'unsubscribed_at': row.unsubscribed_at.isoformat() if row.unsubscribed_at else None,
            'source': row.source, 'page_url': row.page_url}
