"""Operational alerts to a Telegram chat. They never carry personal data: Telegram servers are abroad (152-FZ),
so the full content of a request goes only by e-mail."""

import logging

import httpx

from app.core.config import settings
from app.core.logs import event

logger = logging.getLogger('site.telegram')


def send(text: str) -> None:
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        event(logger, 'telegram_skipped')
        return
    try:
        response = httpx.post(f'https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage', timeout=10,
                              json={'chat_id': settings.telegram_chat_id, 'text': text,
                                    'disable_web_page_preview': True})
        response.raise_for_status()
    except httpx.HTTPError as exc:
        # The e-mail copy of the alert still goes out; a Telegram outage must not block it.
        event(logger, 'telegram_failed', logging.WARNING, error=type(exc).__name__)
