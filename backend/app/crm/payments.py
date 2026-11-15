"""Signed CRM payment facts: idempotent append-only ledger and totals by currency."""

import hashlib
import json
from collections import defaultdict
from decimal import Decimal
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import as_utc, utcnow
from app.core.errors import DomainError
from app.crm import conversions
from app.requests.models import SiteRequest, SiteRequestPayment


class Receipt(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=24, decimal_places=8)
    currency: str = Field(pattern=r'^[A-Za-z]{3}$')
    confirmed_at: AwareDatetime


class Refund(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    payment_id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=24, decimal_places=8)
    currency: str = Field(pattern=r'^[A-Za-z]{3}$')
    refunded_at: AwareDatetime


def _record(db: Session, data: dict[str, Any], kind: str) -> dict[str, Any]:
    row = db.scalar(select(SiteRequest).where(SiteRequest.id == data.get('site_request_id')).with_for_update())
    if row is None:
        return {'ignored': 'SITE_REQUEST_UNKNOWN'}
    try:
        fact = Receipt.model_validate(data.get('payment')) if kind == 'received' else Refund.model_validate(data.get('refund'))
    except ValidationError:
        raise DomainError('CRM_PAYMENT_INVALID', 'Платёж не прошёл проверку', 422) from None
    currency = fact.currency.upper().replace('RUR', 'RUB')
    payment_id = fact.id if isinstance(fact, Receipt) else fact.payment_id
    at = fact.confirmed_at if isinstance(fact, Receipt) else fact.refunded_at
    at = as_utc(at)
    content = {'request_id': row.id, 'kind': kind, 'external_id': fact.id, 'payment_id': payment_id,
               'amount': format(fact.amount.normalize(), 'f'), 'currency': currency, 'at': at.isoformat()}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    existing = db.scalar(select(SiteRequestPayment).where(SiteRequestPayment.kind == kind,
                                                        SiteRequestPayment.external_id == fact.id))
    if existing:
        if existing.payload_hash != digest:
            raise DomainError('CRM_PAYMENT_CONFLICT', 'Подтверждённый факт оплаты уже сохранён с другими данными', 409)
        return {'payment_id': existing.id, 'duplicate': True, 'conversions': 0}
    related = list(db.scalars(select(SiteRequestPayment).where(SiteRequestPayment.payment_id == payment_id)))
    if any(item.site_request_id != row.id or item.currency != currency for item in related):
        raise DomainError('CRM_PAYMENT_CONFLICT', 'Платёж и возврат относятся к разным заявкам или валютам', 409)
    receipt = next((item.amount for item in related if item.kind == 'received'),
                   fact.amount if kind == 'received' else None)
    refund_total = sum((item.amount for item in related if item.kind == 'refunded'), Decimal(0))
    if kind == 'refunded':
        refund_total += fact.amount
    if receipt is not None and refund_total > receipt:
        raise DomainError('CRM_REFUND_AMOUNT', 'Возвраты превышают подтверждённое поступление', 422)
    entry = SiteRequestPayment(site_request_id=row.id, kind=kind, external_id=fact.id, payment_id=payment_id,
                               amount=fact.amount, currency=currency, occurred_at=at, payload_hash=digest)
    db.add(entry)
    db.flush()
    row.crm_updated_at = utcnow()
    row.version += 1
    if data.get('crm_request_id'):
        row.crm_request_id = str(data['crm_request_id'])[:36]
    if data.get('crm_request_number'):
        row.crm_request_number = str(data['crm_request_number'])[:40]
    # Count the first receipt, never call its partial amount the revenue of the entire deal.
    count = conversions.queue(db, row, 'payment_received', at=at.isoformat()) if kind == 'received' else 0
    return {'payment_id': entry.id, 'duplicate': False, 'conversions': count}


def on_received(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    return _record(db, data, 'received')


def on_refunded(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    return _record(db, data, 'refunded')


def totals(entries: list[SiteRequestPayment]) -> list[dict[str, Any]]:
    """A refund arriving first waits for its receipt; money in different currencies is never added together."""
    receipts = {entry.payment_id: entry for entry in entries if entry.kind == 'received'}
    refunded: dict[str, Decimal] = defaultdict(Decimal)
    pending: dict[str, Decimal] = defaultdict(Decimal)
    for entry in entries:
        if entry.kind != 'refunded':
            continue
        if entry.payment_id in receipts:
            refunded[entry.payment_id] += entry.amount
        else:
            pending[entry.currency] += entry.amount
    amounts: dict[str, dict[str, Any]] = {}
    for entry in receipts.values():
        line = amounts.setdefault(entry.currency, {'currency': entry.currency, 'received': Decimal(0),
                                                   'refunded': Decimal(0), 'net': Decimal(0), 'receipts': 0})
        line['received'] += entry.amount
        line['refunded'] += refunded[entry.payment_id]
        line['net'] += max(Decimal(0), entry.amount - refunded[entry.payment_id])
        line['receipts'] += 1
    for currency in pending:
        amounts.setdefault(currency, {'currency': currency, 'received': Decimal(0), 'refunded': Decimal(0),
                                      'net': Decimal(0), 'receipts': 0})
    return [{**line, 'received': str(line['received']), 'refunded': str(line['refunded']), 'net': str(line['net']),
             'pendingRefunds': str(pending[currency])} for currency, line in sorted(amounts.items())]


def for_requests(db: Session, request_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[SiteRequestPayment]] = defaultdict(list)
    if request_ids:
        for entry in db.scalars(select(SiteRequestPayment).where(SiteRequestPayment.site_request_id.in_(request_ids))):
            grouped[entry.site_request_id].append(entry)
    return {identifier: totals(entries) for identifier, entries in grouped.items()}
