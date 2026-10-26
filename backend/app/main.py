"""API of ogk-chem.ru. Contours (TZ 12.2): /api/v1/public/* — the storefront's forms, catalog, search, cart and texts;
/api/v1/admin/* — the admin panel (session, CSRF, roles); /api/v1/crm/* — events of the CRM (flow F2).
/api/v1/health — for the uptime monitor."""

import logging
import re
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.admin.routes import router as admin_router
from app.catalog.routes import router as catalog_router
from app.catalog.search.engine import EngineUnavailable
from app.content.media import router as media_router
from app.content.routes import router as content_router
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.errors import DomainError
from app.core.logs import configure_logging, event
from app.core.monitoring import check_parts, init_sentry
from app.crm.events import router as crm_events_router
from app.requests.routes import router as requests_router
from app.requests.service import FormError
from app.subscriptions.routes import router as subscriptions_router

configure_logging()
init_sentry('api')
logger = logging.getLogger('site.api')

app = FastAPI(title='API сайта ОГК-ХИМ', version='0.1.0', docs_url='/api/docs', redoc_url=None,
              openapi_url='/api/openapi.json',
              description='Каталог, поиск и корзина сайта ogk-chem.ru; приём заявок с форм и их доставка в '
                          '«Реактив CRM» (поток F1).')


def error_body(request: Request, code: str, message: str, field: str | None = None,
               fields: list[dict[str, str]] | None = None) -> dict[str, object]:
    body: dict[str, object] = {'code': code, 'message': message, 'field': field,
                               'requestId': getattr(request.state, 'request_id', None)}
    if fields is not None:
        body['fields'] = fields
    return body


@app.middleware('http')
async def context(request: Request, call_next):
    request_id = request.headers.get('X-Request-ID', '')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', request_id):
        request_id = str(uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f'{{"event": "unhandled_error", "requestId": "{request_id}"}}')
        response = JSONResponse(error_body(request, 'INTERNAL_ERROR', 'Что-то пошло не так. Повторите позже или '
                                           'позвоните нам: +7 495 234 28 63'), status_code=500)
    route = getattr(request.scope.get('route'), 'path', 'unmatched')
    response.headers.update({'X-Request-ID': request_id, 'X-Content-Type-Options': 'nosniff',
                             'Referrer-Policy': 'same-origin'})
    # Catalog answers set their own caching; everything else (forms, the cart, errors) is never cached.
    if response.status_code >= 400 or 'cache-control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    event(logger, 'http_request', requestId=request_id, method=request.method, route=route,
          status=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000, 2))
    return response


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError):
    return JSONResponse(error_body(request, exc.code, exc.message, exc.field), status_code=exc.status)


@app.exception_handler(EngineUnavailable)
async def search_unavailable(request: Request, exc: EngineUnavailable):
    event(logger, 'search_unavailable', logging.ERROR, error=str(exc)[:200])
    return JSONResponse(error_body(request, 'SEARCH_UNAVAILABLE', 'Поиск временно недоступен. Повторите через '
                                   'минуту или позвоните нам: +7 495 234 28 63'), status_code=503)


@app.exception_handler(FormError)
async def form_error(request: Request, exc: FormError):
    return JSONResponse(error_body(request, 'VALIDATION_ERROR', 'Проверьте отмеченные поля формы',
                                   exc.fields[0]['field'] if exc.fields else None, exc.fields), status_code=422)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    fields = [{'field': '.'.join(str(part) for part in error['loc'][1:]), 'message': error['msg']}
              for error in exc.errors()]
    return JSONResponse(error_body(request, 'VALIDATION_ERROR', 'Проверьте отмеченные поля формы',
                                   fields[0]['field'] if fields else None, fields), status_code=422)


@app.exception_handler(OperationalError)
async def database_unavailable(request: Request, exc: OperationalError):
    logger.error('{"event": "database_unavailable"}', exc_info=exc)
    return JSONResponse(error_body(request, 'TEMPORARILY_UNAVAILABLE', 'Сервис временно недоступен. Повторите '
                                   'отправку через минуту или позвоните нам: +7 495 234 28 63'), status_code=503)


@app.get('/health', include_in_schema=False)
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/ready', include_in_schema=False)
def ready():
    try:
        with SessionLocal() as db:
            db.execute(text('SELECT 1'))
        return {'status': 'ready', 'crm_delivery': settings.crm_delivery_enabled}
    except Exception:
        return JSONResponse({'status': 'not_ready'}, status_code=503)


@app.get('/api/v1/health', include_in_schema=False)
def public_health():
    """For an external uptime monitor (Yandex Monitoring, UptimeRobot…): 200 when the database and search work."""
    with SessionLocal() as db:
        parts = check_parts(db)
    healthy = parts.get('database') and parts.get('search')
    return JSONResponse({'status': 'ok' if healthy else 'degraded', **parts}, status_code=200 if healthy else 503)


app.include_router(requests_router, prefix='/api/v1')
app.include_router(catalog_router, prefix='/api/v1')
app.include_router(subscriptions_router, prefix='/api/v1')
app.include_router(content_router, prefix='/api/v1')
app.include_router(admin_router, prefix='/api/v1')
app.include_router(crm_events_router, prefix='/api/v1')
app.include_router(media_router, prefix='/api/v1')
