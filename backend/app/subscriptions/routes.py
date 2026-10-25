"""POST /api/v1/public/subscriptions and /subscriptions/unsubscribe (TZ 11.2, NFR-07)."""

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool

from app.core.db import DB
from app.subscriptions import service
from app.subscriptions.service import SubscribeIn, UnsubscribeIn

router = APIRouter(prefix='/public', tags=['Подписка'])


@router.post('/subscriptions/', include_in_schema=False)
@router.post('/subscriptions', responses={429: {'description': 'Слишком много попыток с адреса'}})
async def subscribe(body: SubscribeIn, request: Request, db: DB) -> dict[str, bool]:
    """Подписка на рассылку: адрес и два согласия — на обработку ПДн и на рекламную рассылку. Ответ одинаковый
    для нового и уже подписанного адреса."""
    ip = request.client.host if request.client else None
    await run_in_threadpool(service.subscribe, db, body, ip, request.headers.get('user-agent'))
    return {'ok': True}


@router.post('/subscriptions/unsubscribe/', include_in_schema=False)
@router.post('/subscriptions/unsubscribe')
async def unsubscribe(body: UnsubscribeIn, db: DB) -> dict[str, bool]:
    """Отписка по ссылке из письма. Ответ одинаковый для любого ключа."""
    await run_in_threadpool(service.unsubscribe, db, body.token)
    return {'ok': True}
