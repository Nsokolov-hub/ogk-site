"""Observability (TZ 12.1): error reports to Sentry or GlitchTip, the health of the parts, a watchdog in the worker.

Error reports carry no personal data: request bodies, cookies and headers other than a few technical ones are
removed before sending. The watchdog alerts the site's Telegram chat about failures nobody would see otherwise.
"""

import logging
import time
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import utcnow
from app.core.logs import event

logger = logging.getLogger('site.monitoring')
SAFE_HEADERS = {'user-agent', 'referer', 'x-request-id', 'content-type', 'accept-language'}


def scrub(report: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    request = report.get('request')
    if isinstance(request, dict):
        request.pop('data', None)
        request.pop('cookies', None)
        headers = request.get('headers')
        if isinstance(headers, dict):
            request['headers'] = {k: v for k, v in headers.items() if k.lower() in SAFE_HEADERS}
    report.pop('user', None)
    return report


def init_sentry(component: str) -> bool:
    if not settings.sentry_dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, server_name=component,
                    send_default_pii=False, traces_sample_rate=0.0, before_send=scrub)  # type: ignore[arg-type]
    return True


def check_parts(db: Session) -> dict[str, bool]:
    """Database, search and Redis: what the uptime monitor and the watchdog look at."""
    parts: dict[str, bool] = {}
    try:
        db.execute(text('SELECT 1'))
        parts['database'] = True
    except Exception:
        parts['database'] = False
    try:
        parts['search'] = httpx.get(f'{settings.meili_url.rstrip("/")}/health', timeout=3).status_code == 200
    except httpx.HTTPError:
        parts['search'] = False
    if settings.redis_url:
        from app.core.ratelimit import redis_client

        try:
            parts['redis'] = bool(redis_client().ping())
        except Exception:
            parts['redis'] = False
    return parts


class Watchdog:
    """Every few minutes in the worker: search down, the queue stuck, letters failing. One alert per hour each."""

    def __init__(self, every_seconds: float = 300, repeat_after: timedelta = timedelta(hours=1)) -> None:
        self.every = every_seconds
        self.repeat_after = repeat_after
        self.last_run = 0.0
        self.alerted: dict[str, Any] = {}

    def due(self) -> bool:
        return time.monotonic() - self.last_run >= self.every

    def problems(self, db: Session) -> list[tuple[str, str]]:
        from app.outbox.models import OutboxEvent

        found: list[tuple[str, str]] = []
        parts = check_parts(db)
        for name, label in (('search', 'поиск (Meilisearch) не отвечает'), ('redis', 'Redis не отвечает')):
            if parts.get(name) is False:
                found.append((name, label))
        now = utcnow()
        kinds = select(OutboxEvent.kind).where(OutboxEvent.status == 'pending',
                                               OutboxEvent.created_at < now - timedelta(minutes=30))
        if not settings.crm_delivery_enabled:
            kinds = kinds.where(OutboxEvent.kind.not_like('crm.%'))
        stuck = db.scalar(select(func.count()).select_from(kinds.subquery())) or 0
        if stuck:
            found.append(('queue', f'очередь стоит: {stuck} задач ждут дольше 30 минут'))
        failed = db.scalar(select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.status == 'failed', OutboxEvent.finished_at >= now - timedelta(hours=1),
            OutboxEvent.kind.not_like('crm.%'))) or 0
        if failed:
            found.append(('failed', f'за час не выполнено задач очереди: {failed} (письма, индекс)'))
        return found

    def run(self, db: Session, send: Any) -> list[str]:
        self.last_run = time.monotonic()
        now = utcnow()
        sent: list[str] = []
        for key, label in self.problems(db):
            last = self.alerted.get(key)
            if last is None or now - last >= self.repeat_after:
                self.alerted[key] = now
                event(logger, 'watchdog_alert', logging.WARNING, problem=key)
                send(f'Сайт ({settings.environment}): {label}')
                sent.append(key)
        return sent
