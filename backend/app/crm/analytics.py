"""Reports of Yandex Metrica and Webmaster for the CRM (my-crm-project «Аналитика» → «Сайт: Метрика и Вебмастер»).

The CRM asks with the signature of its events (app.crm.events.verify): the same shared key, the same headers, the
same list of addresses. One endpoint, the action in the body: ``report`` and ``refresh`` give the snapshot of a
period; ``connect``, ``disconnect``, ``goals`` and ``sitemap`` do what the buttons of the admin panel do and are
written to its journal under the name of the CRM employee. The Yandex token travels from the CRM to the site only,
never back: answers name its last four characters.
"""

from types import SimpleNamespace
from typing import Any, Literal, cast

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.admin.routes import analytics as admin
from app.core.config import settings
from app.core.db import DB
from app.core.errors import DomainError
from app.crm.events import address_allowed, verify

router = APIRouter(include_in_schema=False)


class AnalyticsIn(BaseModel):
    action: Literal['report', 'refresh', 'connect', 'disconnect', 'goals', 'sitemap']
    period: int = 30
    token: str | None = Field(default=None, max_length=400)
    author: str = Field(default='сотрудник', min_length=1, max_length=100)


def handle(db: Session, body: AnalyticsIn) -> dict[str, Any]:
    # The journal of the admin panel takes anything with a name; the CRM employee is not a staff member here.
    actor = cast(Any, SimpleNamespace(id=None, name=f'{body.author} (CRM)'))
    if body.action == 'report':
        return admin.analytics(db, body.period)
    if body.action == 'refresh':
        return admin.refresh(db, body.period)
    if body.action == 'connect':
        if not body.token:
            raise DomainError('TOKEN_INVALID', 'Вставьте токен Яндекса', 422, 'token')
        return admin.connect(admin.TokenIn(token=body.token), actor, db)
    if body.action == 'disconnect':
        return admin.disconnect(actor, db)
    if body.action == 'goals':
        return admin.goals(actor, db)
    return admin.sitemap(actor, db)


@router.post('/crm/analytics')
async def analytics(request: Request, db: DB) -> dict[str, Any]:
    if not settings.crm_events_secret:
        raise DomainError('CRM_EVENTS_DISABLED', 'Связь с CRM не настроена (CRM_EVENTS_SECRET)', 503)
    if not address_allowed(request.client.host if request.client else None):
        raise DomainError('CRM_ADDRESS_FORBIDDEN', 'Адрес не разрешён', 403)
    raw = await request.body()
    verify({key.lower(): value for key, value in request.headers.items()}, raw)
    try:
        body = AnalyticsIn.model_validate_json(raw)
    except ValidationError:
        raise DomainError('CRM_REQUEST_INVALID', 'Запрос CRM не прошёл проверку', 422) from None
    return await run_in_threadpool(handle, db, body)
