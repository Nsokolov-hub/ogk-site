"""Yandex Metrica and Webmaster in the admin panel (app.analytics.yandex): the reports, the token, goals, Sitemap.

Everyone with the summary page sees the reports; connecting the token, creating goals and adding the Sitemap are
the administrator's (settings.write). The token never leaves the server: the journal and the answers name only its
last four characters.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.admin.audit import record
from app.admin.security import StaffDep, requires
from app.analytics import yandex
from app.catalog import competitors
from app.catalog.settings import get_setting, set_setting
from app.core.db import DB
from app.core.errors import DomainError

router = APIRouter()


@router.get('/analytics', dependencies=[requires('dashboard')])
def analytics(db: DB, period: int = 30) -> dict[str, Any]:
    if period not in yandex.PERIODS:
        raise DomainError('PERIOD_INVALID', 'Период — 7, 30 или 90 дней', 422, 'period')
    return yandex.report(db, period)


@router.post('/analytics/refresh', dependencies=[requires('settings.write')])
def refresh(db: DB, period: int = 30) -> dict[str, Any]:
    if not yandex.token(db):
        raise DomainError('YANDEX_NOT_CONNECTED', 'Сначала подключите Яндекс в настройках', 409)
    yandex.refresh(db)
    return analytics(db, period)


class TokenIn(BaseModel):
    token: str


@router.put('/analytics/token', dependencies=[requires('settings.write')])
def connect(body: TokenIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    access = yandex.connect(db, body.token, staff.name)
    state = yandex.status(db)
    record(db, staff, 'setting', 'yandex_token', 'update',
           f'подключён Яндекс: токен …{state["tail"]}' + (f', аккаунт {state["login"]}' if state['login'] else ''))
    goals: list[dict[str, Any]] | str = 'нет доступа к Метрике'
    if access['metrika']['ok']:
        try:
            goals = create_goals(db, staff)
        except DomainError as exc:
            goals = exc.message
    return {'status': state, 'access': access, 'goals': goals}


@router.delete('/analytics/token', dependencies=[requires('settings.write')])
def disconnect(staff: StaffDep, db: DB) -> dict[str, Any]:
    yandex.disconnect(db)
    record(db, staff, 'setting', 'yandex_token', 'delete', 'отключён Яндекс')
    return {'status': yandex.status(db)}


def create_goals(db: DB, staff: StaffDep) -> list[dict[str, Any]]:
    result = yandex.ensure_goals(db)
    created = [g['identifier'] for g in result if g['state'] == 'created']
    if created:
        record(db, staff, 'setting', 'metrika_goals', 'create', f'цели Метрики: {", ".join(created)}')
    return result


@router.post('/analytics/goals', dependencies=[requires('settings.write')])
def goals(staff: StaffDep, db: DB) -> dict[str, Any]:
    return {'goals': create_goals(db, staff)}


@router.post('/analytics/sitemap', dependencies=[requires('settings.write')])
def sitemap(staff: StaffDep, db: DB) -> dict[str, Any]:
    result = yandex.add_sitemap(db)
    if result['state'] == 'added':
        record(db, staff, 'setting', 'webmaster_sitemap', 'create', f'Sitemap в Вебмастере: {result["url"]}')
    return result


# ── stock of suppliers (app.catalog.competitors) ──

@router.get('/competitors', dependencies=[requires('dashboard')])
def suppliers(db: DB) -> dict[str, Any]:
    return competitors.status(db)


@router.post('/competitors/check', dependencies=[requires('settings.write')])
def check_suppliers(staff: StaffDep, db: DB) -> dict[str, Any]:
    """Check now instead of in a few days: the worker starts within its next turn."""
    if not get_setting(db, 'competitor_run'):
        results = get_setting(db, 'competitor_results') or {}
        set_setting(db, 'competitor_results', {**results, 'finishedAt': None})
        record(db, staff, 'setting', 'competitor_stock', 'update', 'проверка складов поставщиков — сейчас')
    return {**competitors.status(db), 'due': competitors.due(db)}
