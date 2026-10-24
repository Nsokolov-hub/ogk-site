"""Antispam of the forms (RFQ-06): trap field, minimal filling time, limits per address, SmartCaptcha on suspicion.

A person never sees a captcha without a reason: it is asked only when the form was filled faster than a person
can or the address sends too many requests. Without a configured SmartCaptcha key such requests pass and are
marked suspicious for the managers.
"""

import hashlib
import logging
from datetime import timedelta

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import DomainError
from app.core.logs import event
from app.requests.models import RateEvent
from app.requests.schemas import RequestIn

logger = logging.getLogger('site.antispam')
SMARTCAPTCHA_URL = 'https://smartcaptcha.yandexcloud.net/validate'


def address_key(ip: str | None) -> str:
    return hashlib.sha256(f'site-rate:{ip or "unknown"}'.encode()).hexdigest()


def recent(db: Session, key: str, minutes: int) -> int:
    since = utcnow() - timedelta(minutes=minutes)
    return db.scalar(select(func.count()).select_from(RateEvent)
                     .where(RateEvent.key == key, RateEvent.created_at >= since)) or 0


def captcha_valid(token: str, ip: str | None) -> bool:
    try:
        response = httpx.post(SMARTCAPTCHA_URL, timeout=5, data={
            'secret': settings.smartcaptcha_server_key, 'token': token, 'ip': ip or ''})
        return response.status_code == 200 and response.json().get('status') == 'ok'
    except (httpx.HTTPError, ValueError):
        # The captcha service is unreachable: let the person through rather than lose a lead.
        event(logger, 'smartcaptcha_unavailable', logging.WARNING)
        return True


def check(db: Session, data: RequestIn, ip: str | None) -> bool:
    """Record the attempt; True when the request is suspicious but allowed. Raises 429 or 428."""
    key = address_key(ip)
    hard = recent(db, key, settings.rate_hard_window_minutes)
    if hard >= settings.rate_hard_limit:
        raise DomainError('RATE_LIMITED', 'Слишком много заявок с вашего адреса. Позвоните нам или повторите позже',
                          429)
    soft = recent(db, key, settings.rate_soft_window_minutes)
    db.add(RateEvent(key=key))
    db.flush()
    suspicious = data.antispam.elapsed_ms < settings.min_fill_ms or soft >= settings.rate_soft_limit
    if not suspicious:
        return False
    if not settings.smartcaptcha_server_key:
        return True
    if data.captcha_token and captcha_valid(data.captcha_token, ip):
        return False
    raise DomainError('CAPTCHA_REQUIRED', 'Подтвердите, что вы не робот', 428, 'captchaToken')


def prune(db: Session) -> int:
    """Forget attempts older than a day; the limits look back an hour at most."""
    result = db.execute(delete(RateEvent).where(RateEvent.created_at < utcnow() - timedelta(days=1)))
    return int(getattr(result, 'rowcount', 0) or 0)
