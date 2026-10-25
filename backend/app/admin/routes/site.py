"""Settings of the site and the summary page (ADM-09, ADM-10, ADM-11).

Contacts and requisites are the one source for the header, the footer and Organization; the threshold and the
weights of completeness re-count the whole catalog in the background; the feed check lists what Direct would refuse.
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.admin.audit import record
from app.admin.editables import queue_revalidate
from app.admin.models import ContentPage, Draft, ImportUpload
from app.admin.routes.queues import summary as queue_summary
from app.admin.security import StaffDep, requires
from app.catalog import pages
from app.catalog.models import ImportBatch, Product
from app.catalog.settings import DEFAULTS, get_setting, set_setting
from app.core.config import settings
from app.core.db import DB, utcnow
from app.core.errors import DomainError
from app.outbox.models import OutboxEvent
from app.requests.models import SiteRequest

router = APIRouter()


@router.get('/dashboard', dependencies=[requires('dashboard')])
def dashboard(db: DB) -> dict[str, Any]:
    week = utcnow() - timedelta(days=7)
    statuses = dict(db.execute(select(Product.status, func.count()).group_by(Product.status)).all())
    last_batch = db.scalar(select(ImportBatch).order_by(ImportBatch.started_at.desc()).limit(1))
    return {
        'products': {'byStatus': statuses, 'total': sum(statuses.values()),
                     'indexable': db.scalar(select(func.count()).select_from(Product)
                                            .where(Product.indexable.is_(True))) or 0},
        'queues': queue_summary(db),
        'requests': {
            'week': db.scalar(select(func.count()).select_from(SiteRequest).where(SiteRequest.created_at >= week)) or 0,
            'undelivered': db.scalar(select(func.count()).select_from(SiteRequest)
                                     .where(SiteRequest.status != 'delivered')) or 0,
            'failed': db.scalar(select(func.count()).select_from(SiteRequest)
                                .where(SiteRequest.status == 'failed')) or 0},
        'content': {'pages': db.scalar(select(func.count()).select_from(ContentPage)) or 0,
                    'drafts': db.scalar(select(func.count()).select_from(Draft)) or 0,
                    'scheduled': db.scalar(select(func.count()).select_from(Draft)
                                           .where(Draft.publish_at.is_not(None))) or 0},
        'lastImport': {'fileName': last_batch.file_name, 'status': last_batch.status,
                       'startedAt': last_batch.started_at.isoformat(), 'counters': last_batch.counters}
        if last_batch else None,
        'integration': integration(db),
    }


def integration(db: DB) -> dict[str, Any]:
    """Связь с CRM (ADM-10): включена ли доставка, когда ушла последняя заявка, что ждёт в очереди."""
    last = db.scalar(select(func.max(SiteRequest.delivered_at)))
    pending = db.scalar(select(func.count()).select_from(OutboxEvent).where(
        OutboxEvent.status == 'pending', OutboxEvent.kind.like('crm.%'))) or 0
    return {'crmUrl': settings.crm_url, 'deliveryEnabled': settings.crm_delivery_enabled,
            'lastDeliveredAt': last.isoformat() if last else None, 'pending': pending,
            'brandsSyncedAt': get_setting(db, 'brands_synced_at'), 'brandsSyncRunAt': get_setting(db, 'brands_sync_run_at')}


EDITABLE = {'site': 'settings.write', 'counters': 'settings.write', 'mail': 'settings.write',
            'index_threshold': 'settings.write', 'completeness_weights': 'settings.write',
            'hide_controlled': 'settings.write', 'feed': 'feeds.write'}
RECOUNT = ('index_threshold', 'completeness_weights', 'hide_controlled')


@router.get('/settings', dependencies=[requires('settings.read')])
def read_settings(db: DB) -> dict[str, Any]:
    out = {key: get_setting(db, key) for key in EDITABLE}
    out['integration'] = integration(db)
    out['server'] = {'environment': settings.environment, 'siteUrl': settings.site_url,
                     'salesEmail': settings.sales_email, 'alertEmails': settings.alert_emails}
    return out


class SettingIn(BaseModel):
    value: Any


def check_setting(key: str, value: Any) -> Any:
    if key == 'site':
        if not isinstance(value, dict) or not isinstance(value.get('ru'), dict):
            raise DomainError('VALUE_INVALID', 'Нужны контакты на русском', 422, 'ru')
        for lang in ('ru', 'en'):
            data = value.get(lang) or {}
            for field in ('phone', 'emails', 'address', 'legal', 'docs'):
                if lang == 'ru' and not isinstance(data.get(field), dict):
                    raise DomainError('VALUE_INVALID', f'Заполните блок {field}', 422, f'{lang}.{field}')
        return {'ru': value['ru'], 'en': value.get('en') or value['ru']}
    if key == 'counters':
        ym = value.get('ym') if isinstance(value, dict) else None
        ga = value.get('ga') if isinstance(value, dict) else None
        if ym not in (None, '') and not str(ym).isdigit():
            raise DomainError('VALUE_INVALID', 'Номер счётчика Метрики — цифры', 422, 'ym')
        if ga not in (None, '') and not str(ga).startswith('G-'):
            raise DomainError('VALUE_INVALID', 'Идентификатор GA4 начинается с G-', 422, 'ga')
        return {'ym': int(ym) if ym not in (None, '') else None, 'ga': ga or None}
    if key == 'index_threshold':
        if not isinstance(value, int) or not 0 <= value <= 100:
            raise DomainError('VALUE_INVALID', 'Порог — от 0 до 100', 422, 'value')
        return value
    if key == 'completeness_weights':
        allowed = set(DEFAULTS['completeness_weights'])
        if not isinstance(value, dict) or set(value) != allowed or not all(isinstance(v, int) and v >= 0
                                                                          for v in value.values()):
            raise DomainError('VALUE_INVALID', f'Веса: {", ".join(sorted(allowed))} — целые неотрицательные', 422)
        if sum(value.values()) != 100:
            raise DomainError('VALUE_INVALID', 'Сумма весов — 100', 422, 'value')
        return value
    if key == 'hide_controlled':
        return bool(value)
    if key == 'feed':
        if not isinstance(value, dict):
            raise DomainError('VALUE_INVALID', 'Нужны разделы и бренды фида', 422)
        return {'categories': [str(c) for c in value.get('categories') or []],
                'brands': [str(b) for b in value.get('brands') or []]}
    if key == 'mail':
        return {k: str((value or {}).get(k) or '').strip() for k in DEFAULTS['mail']}
    return value


@router.put('/settings/{key}')
def save_setting(key: str, body: SettingIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    if key not in EDITABLE:
        raise DomainError('NOT_FOUND', 'Нет такой настройки', 404)
    staff.require(EDITABLE[key])
    value = check_setting(key, body.value)
    before = get_setting(db, key)
    set_setting(db, key, value)
    record(db, staff, 'setting', key, 'update', key, before, value)
    if key in RECOUNT:
        # The whole catalog: completeness, indexing and the index — in the background (app.outbox.worker).
        db.add(OutboxEvent(event_key=f'catalog-refresh:{utcnow().timestamp()}', kind='catalog.refresh', payload={}))
    queue_revalidate(db, ['content', 'catalog'])
    return read_settings(db)


@router.get('/feed/check', dependencies=[requires('feeds.read')])
def feed_check(db: DB) -> dict[str, Any]:
    """Проверка YML-фида (ADM-11): сколько позиций попадёт и что Директ не примет."""
    feed = pages.feed(db, limit=50000)
    items = feed.get('items') or []
    problems: list[str] = []
    no_category = sum(1 for i in items if not i.get('categorySlug'))
    long_names = sum(1 for i in items if len(str(i.get('name') or '')) > 150)
    if not items:
        problems.append('В фиде нет позиций: проверьте разделы и бренды в настройке фида')
    if no_category:
        problems.append(f'Без раздела: {no_category} — Директ их не покажет')
    if long_names:
        problems.append(f'Названия длиннее 150 символов: {long_names} — Директ обрежет')
    problems.append('Цен в фиде нет (ТЗ 15.4): форматы Директа, которым нужна цена, работать не будут')
    return {'items': len(items), 'categories': len(feed.get('categories') or []), 'problems': problems,
            'setting': get_setting(db, 'feed'), 'url': f'{settings.site_url.rstrip("/")}/feeds/yandex-direct.yml'}


@router.get('/import/active', dependencies=[requires('import.read')])
def active_import(db: DB) -> dict[str, Any] | None:
    row = db.scalar(select(ImportUpload).where(ImportUpload.status.in_(('queued', 'running'))).limit(1))
    return {'id': row.id, 'fileName': row.file_name, 'status': row.status} if row else None
