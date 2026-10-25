"""The journal of site requests and the subscribers (ADM-08).

Every role sees the journal: number, type, time, delivery to the CRM and its number. Contacts, companies and the
content of requests, and the list of subscribers, are personal data: administrators only.
"""

from typing import Any

from fastapi import APIRouter, Response
from sqlalchemy import func, or_, select

from app.admin.audit import record
from app.admin.security import StaffDep, requires
from app.cli import resend as resend_request
from app.core.db import DB
from app.core.errors import DomainError
from app.requests.models import DeliveryAttempt, SiteRequest, SiteRequestAttachment, SiteRequestItem
from app.subscriptions.models import Subscriber
from app.subscriptions.service import export_csv

router = APIRouter()
KIND_NAMES = {'product_rfq': 'Корзина', 'one_click': 'В 1 клик', 'service': 'Услуга', 'general': 'Общая форма'}


def mask(value: str | None) -> str | None:
    if not value:
        return value
    return value[:1] + '•••' + (value[-2:] if len(value) > 4 else '')


def request_out(row: SiteRequest, items: int, pii: bool) -> dict[str, Any]:
    show = (lambda v: v) if pii else mask
    return {'id': row.id, 'number': row.number, 'kind': row.kind, 'kindName': KIND_NAMES.get(row.kind, row.kind),
            'lang': row.lang, 'createdAt': row.created_at.isoformat(), 'status': row.status,
            'crmNumber': row.crm_number, 'deliveredAt': row.delivered_at.isoformat() if row.delivered_at else None,
            'deliveryError': row.delivery_error, 'suspicious': row.suspicious, 'items': items,
            'company': show(row.company), 'customer': show(row.customer_name), 'email': show(row.email),
            'phone': show(row.phone), 'channel': (row.attribution or {}).get('channel')}


@router.get('/requests', dependencies=[requires('requests.journal')])
def journal(staff: StaffDep, db: DB, status: str = '', q: str = '', page: int = 1) -> dict[str, Any]:
    pii = staff.can('requests.pii')
    statement = select(SiteRequest)
    if status:
        statement = statement.where(SiteRequest.status == status)
    if q.strip():
        like = f'%{q.strip()}%'
        conditions: list[Any] = [SiteRequest.number.ilike(like), SiteRequest.crm_number.ilike(like)]
        if pii:
            conditions += [SiteRequest.company.ilike(like), SiteRequest.email.ilike(like),
                           SiteRequest.phone.ilike(like), SiteRequest.inn == q.strip()]
        statement = statement.where(or_(*conditions))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(db.scalars(statement.order_by(SiteRequest.created_at.desc()).offset((max(page, 1) - 1) * 50)
                           .limit(50)))
    counts = dict(db.execute(select(SiteRequestItem.request_id, func.count())
                             .where(SiteRequestItem.request_id.in_([r.id for r in rows]))
                             .group_by(SiteRequestItem.request_id)).all()) if rows else {}
    by_status = dict(db.execute(select(SiteRequest.status, func.count()).group_by(SiteRequest.status)).all())
    return {'total': total, 'counts': by_status, 'pii': pii,
            'items': [request_out(r, counts.get(r.id, 0), pii) for r in rows]}


@router.get('/requests/{request_id}', dependencies=[requires('requests.journal')])
def request_card(request_id: str, staff: StaffDep, db: DB) -> dict[str, Any]:
    row = db.get(SiteRequest, request_id)
    if row is None:
        raise DomainError('NOT_FOUND', 'Заявка не найдена', 404)
    pii = staff.can('requests.pii')
    items = list(db.scalars(select(SiteRequestItem).where(SiteRequestItem.request_id == row.id)
                            .order_by(SiteRequestItem.position)))
    attempts = db.scalars(select(DeliveryAttempt).where(DeliveryAttempt.request_id == row.id)
                          .order_by(DeliveryAttempt.attempt))
    files = db.scalars(select(SiteRequestAttachment).where(SiteRequestAttachment.request_id == row.id))
    out = request_out(row, len(items), pii)
    out.update({
        'attempts': [{'attempt': a.attempt, 'at': a.created_at.isoformat(), 'outcome': a.outcome,
                      'statusCode': a.status_code, 'error': a.error_code, 'durationMs': a.duration_ms}
                     for a in attempts],
        'attachments': [{'name': f.file_name, 'size': f.size} for f in files] if pii else [],
        'pageUrl': row.page_url, 'attribution': row.attribution,
    })
    if pii:
        out.update({'inn': row.inn, 'city': row.city, 'comment': row.comment, 'service': row.service,
                    'positions': [{'name': i.name, 'brand': i.brand, 'catalogNumber': i.catalog_number, 'cas': i.cas,
                                   'packaging': i.packaging, 'quantity': str(i.quantity), 'unit': i.unit,
                                   'analogue': i.analogue, 'comment': i.comment} for i in items]})
    return out


@router.post('/requests/{request_id}/resend', dependencies=[requires('requests.resend')])
def resend(request_id: str, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Отправить в CRM повторно: новое окно доставки на 24 часа (RFQ-07)."""
    row = db.get(SiteRequest, request_id)
    if row is None:
        raise DomainError('NOT_FOUND', 'Заявка не найдена', 404)
    try:
        message = resend_request(db, row.number)
    except SystemExit as exc:
        raise DomainError('RESEND_REFUSED', str(exc), 409) from None
    record(db, staff, 'request', row.id, 'resend', row.number)
    return {'message': message}


@router.get('/subscribers', dependencies=[requires('subscribers.read')])
def subscribers(db: DB, status: str = '', q: str = '', page: int = 1) -> dict[str, Any]:
    statement = select(Subscriber)
    if status:
        statement = statement.where(Subscriber.status == status)
    if q.strip():
        statement = statement.where(Subscriber.email.ilike(f'%{q.strip()}%'))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(Subscriber.created_at.desc()).offset((max(page, 1) - 1) * 100).limit(100))
    counts = dict(db.execute(select(Subscriber.status, func.count()).group_by(Subscriber.status)).all())
    return {'total': total, 'counts': counts, 'items': [{
        'id': s.id, 'email': s.email, 'lang': s.lang, 'status': s.status, 'source': s.source,
        'consentAt': s.marketing_consent_at.isoformat(),
        'unsubscribedAt': s.unsubscribed_at.isoformat() if s.unsubscribed_at else None,
        'inCrm': s.crm_synced_at is not None} for s in rows]}


@router.get('/subscribers/export', dependencies=[requires('subscribers.read')])
def export(staff: StaffDep, db: DB, all: bool = False) -> Response:
    record(db, staff, 'subscriber', 'export', 'export', 'выгрузка подписчиков в CSV')
    return Response(export_csv(db, None if all else 'active'), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename="subscribers.csv"'})
