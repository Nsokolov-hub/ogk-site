"""Full traversal, fair source progress and card-level error isolation."""

from typing import Any

import httpx
from sqlalchemy import func, select

from app.catalog import competitors
from app.catalog.models import CompetitorOffer
from app.catalog.settings import get_setting, set_setting
from app.catalog.stock_sources.base import Offer, Page, ParseChanged
from app.core.config import settings
from tests.catalog.test_competitors import skygen_card


def test_batch_budget_preserves_all_pages_and_other_sources_progress(sessions, monkeypatch):
    calls = []

    def page(client, task, wanted):
        calls.append((task['s'], task['page']))
        if task['page'] == 1:
            return Page(tasks=[{**task, 'page': n} for n in range(2, 132)])
        return Page(offers=[Offer(str(task['page']), 'New maker', f'NEW-{task["page"]}', 'New product',
                                 str(competitors.META[task['s']]['url']), pack='1 g')])

    monkeypatch.setattr(settings, 'competitor_stock_enabled', True)
    monkeypatch.setattr(competitors, 'pause', lambda _: None)
    monkeypatch.setattr(competitors, 'http_client', lambda: httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(404))))
    for source in ('chimmed', 'skygen'):
        monkeypatch.setitem(competitors.SOURCES, source, page)
        monkeypatch.setitem(competitors.FIRST, source, {'s': source, 'page': 1})
    with sessions.begin() as db:
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'),
                                            'sources': ['chimmed', 'skygen'], 'max_pages_per_source': 2})
    run = competitors.turn(sessions, seconds=3600)
    assert run and not run.get('finishedAt') and len(run['queue']) == 258
    assert calls[:4] == [('chimmed', 1), ('skygen', 1), ('chimmed', 2), ('skygen', 2)]
    # A subsequent worker uses persisted state; all 131 pages/source, including the old 120-page tail, survive.
    result = competitors.run_all(sessions)
    assert result and all(s['complete'] and s['pages'] == 131 and s['truncated'] == 0
                          for s in result['sources'].values())
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(CompetitorOffer)) == 260


def test_bad_detail_page_does_not_discard_sibling_pages(sessions, monkeypatch):
    def page(client, task, wanted):
        if task.get('page') == 2:
            raise ParseChanged('one discontinued card')
        if task.get('page') == 3:
            return Page(offers=[Offer('last', 'Unknown', 'SKU3', 'Good product', competitors.CHIMMED + '/products/storage')])
        return Page(tasks=[{**task, 'page': 2}, {**task, 'page': 3}])

    monkeypatch.setattr(settings, 'competitor_stock_enabled', True)
    monkeypatch.setattr(competitors, 'pause', lambda _: None)
    monkeypatch.setattr(competitors, 'http_client', lambda: httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(404))))
    monkeypatch.setitem(competitors.SOURCES, 'chimmed', page)
    with sessions.begin() as db:
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'), 'sources': ['chimmed']})
    result = competitors.run_all(sessions)
    assert result and result['sources']['chimmed']['incomplete'] == 'one discontinued card'
    with sessions() as db:
        assert db.scalar(select(CompetitorOffer.catalog_number)) == 'SKU3'


def test_skygen_keeps_good_cards_unknown_brands_and_explicit_packs_without_form():
    raw = skygen_card(1, 'SKU-1', 'New manufacturer', 5).replace('Стандарт 1 &amp; Co', 'Стандарт 1, 25 mg')
    raw = raw.replace('<form action="/catalog/item_1/" method="post">', '<div>').replace('</form>', '</div>')
    broken = skygen_card(2, 'SKU-2', 'Maker', 1).replace('Доступно: 1', 'Уточните наличие')
    response = raw + broken + '<a href="?PAGEN_1=1421">Последняя</a>'
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=response))) as client:
        out = competitors.skygen_page(client, {'s': 'skygen', 'page': 1}, lambda _: False)
    assert len(out.offers) == 1 and out.offers[0].pack == '25 mg' and out.offers[0].brand_name == 'New manufacturer'
    assert out.incomplete and out.tasks == [{'s': 'skygen', 'page': 2}]


def test_new_pages_do_not_inherit_retries_and_discovery_has_no_200_link_cutoff():
    from app.catalog.stock_sources.html import tasks

    pages, truncated = tasks([f'https://source.test/catalog/?PAGEN_1={n}' for n in range(1, 302)], 'diam')
    assert len(pages) == 301 and truncated == 0
    run: dict[str, Any] = {'queue': [], 'scheduled': {}, 'stats': {}}
    competitors._enqueue(run, 'diam', [{**pages[-1], 'tries': 2}, pages[-1]])
    assert run['queue'] == [pages[-1]] and 'tries' not in run['queue'][0]


def test_skygen_conflicting_article_and_visible_pack_remains_for_review():
    raw = skygen_card(1, 'SKU-100MG', 'Maker', 5).replace('Стандарт 1 &amp; Co', 'Стандарт 1, 25 mg')
    offer = competitors.skygen_offers(raw)[0]
    assert offer.pack == '25 mg' and offer.review_only


def test_robots_prerequisite_failure_stops_source_once_even_with_a_saved_queue(sessions, monkeypatch):
    calls = []

    def handle(request):
        calls.append(str(request.url))
        assert request.url.path == '/robots.txt'
        return httpx.Response(302, headers={'Location': '/private/'})

    monkeypatch.setattr(settings, 'competitor_stock_enabled', True)
    monkeypatch.setattr(competitors, 'pause', lambda _: None)
    monkeypatch.setattr(competitors, 'http_client', lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    with sessions.begin() as db:
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'), 'sources': ['skygen']})
        run = competitors.start(db, competitors.utcnow())
        competitors._enqueue(run, 'skygen', [{'s': 'skygen', 'page': n} for n in range(2, 250)])
        set_setting(db, 'competitor_run', run)
    result = competitors.run_all(sessions)
    assert result and result['sources']['skygen']['refused'] == 'redirect_requires_review'
    assert len(calls) == 1
