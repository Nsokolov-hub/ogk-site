"""Лаверна's public catalogue currently exposes identity, without verifiable stock.

The observed Pharmaffiliates cards and details say «Запросить стоимость». Generic manufacturer warehouse claims
and dated sale articles are not fresh local stock, so this adapter reports the missing evidence explicitly.
"""

from collections.abc import Callable
from typing import Any

import httpx

from app.catalog.stock_sources.base import Page, ParseChanged, check_answer
from app.catalog.stock_sources.html import Document

ORIGIN = 'https://laverna-xxi.ru'
START = f'{ORIGIN}/catalog/385/'


def parse(page: str) -> Page:
    root = Document(page).root
    if not root.find('h1'):
        raise ParseChanged('laverna_catalogue_missing')
    return Page(incomplete='no_stock_evidence')


def page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    return parse(check_answer(client.get(task['url'])).text)
