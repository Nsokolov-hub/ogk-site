"""Revisit real Лаверна catalogue/detail pages, without treating a quote button as warehouse stock."""

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.catalog.stock_sources.base import Page, ParseChanged, check_answer
from app.catalog.stock_sources.html import Document
from app.catalog.stock_sources.probes import _links, _tasks, structured_stock

ORIGIN = 'https://laverna-xxi.ru'
START = f'{ORIGIN}/catalog/385/'


def parse(page: str, url: str = START) -> Page:
    root = Document(page).root
    if not root.find('h1'):
        raise ParseChanged('laverna_catalogue_missing')
    offers = structured_stock(page, url)
    return Page(offers=offers, incomplete='public_stock_sample_requires_full_feed' if offers else 'no_stock_evidence')


def page(client: httpx.Client, task: dict[str, Any], wanted: Callable[[str], bool]) -> Page:
    url, depth = task['url'], task.get('probe_depth', 0)
    content = check_answer(client.get(url)).text
    result = parse(content, url)
    if depth < 2:
        # Public navigation actually links these reagent/standard/column categories. Do not follow Bitrix
        # PAGEN URLs (disallowed by this supplier's robots) or synthesize an alternate pagination endpoint.
        categories = _links(content, url, lambda link: not urlsplit(link).query and
                            urlsplit(link).path in ('/catalog/454/', '/catalog/298/')) if depth == 0 else []
        products = _links(content, url, lambda link: not urlsplit(link).query and
                          bool(re.fullmatch(r'/catalog/\d+/\d+/', urlsplit(link).path)))
        result.tasks = _tasks('laverna', categories, 1) + _tasks('laverna', products[:3], 2)
    return result
