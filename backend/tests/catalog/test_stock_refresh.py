"""Frequent verifications are independent of discovery and apply delayed stock immediately."""

import html
import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app.catalog import competitors, stock_refresh
from app.catalog.models import Brand, CompetitorOffer, Packaging, Product
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.core.db import as_utc, utcnow
from tests.catalog.test_competitors import product


@pytest.fixture
def refresh_config(sessions, monkeypatch):
    monkeypatch.setattr(settings, 'competitor_stock_enabled', True)
    monkeypatch.setattr(competitors, 'pause', lambda _: None)
    with sessions.begin() as db:
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'),
                                            'sources': ['chimmed'], 'refresh_hours': 2, 'fresh_hours': 6})


def warehouse_page():
    makers = html.escape(json.dumps({'N': [['neoFroxx', 'Unknown manufacturer']]}), quote=True)
    return f"<main data-letters-and-manufactors='{makers}'></main>"


def row(identifier: int, number: str, *, delayed: bool):
    return {'id': identifier, 'name': f'neoFroxx {number}', 'art_number': number, 'cas': '369-07-3',
            'packing': '100 г', 'price': '93 562,14 ₽', 'manufactorName': 'neoFroxx',
            'storage_product': True, 'is_delayed': delayed, 'url': f'product-{identifier}'}


@pytest.fixture
def known_stock(sessions):
    with sessions.begin() as db:
        brand = Brand(name='neoFroxx', slug='neofroxx')
        db.add(brand)
        db.flush()
        bad = product(db, brand, '2028GR100', packs=('2028GR100',), default_pack='100 g')
        good = product(db, brand, '1779GR100', packs=('1779GR100',), default_pack='100 g')
        offer = competitors.Offer('16914295', 'neoFroxx', '2028GR100', 'Target',
                                  competitors.CHIMMED + '/products/product-16914295-id=16914295', pack='100 г')
        competitors.save(db, 'chimmed', [offer], competitors.Brands(db), utcnow() - timedelta(hours=1))
        assert bad.supplier_stock
        return bad.id, good.id


def test_refresh_due_during_active_discovery_and_uses_start_time(sessions, refresh_config):
    now = utcnow()
    with sessions.begin() as db:
        set_setting(db, 'competitor_run', {'startedAt': (now - timedelta(hours=14)).isoformat(),
                                          'queue': [{'s': 'chimmed', 'k': 'start'}]})
        set_setting(db, 'competitor_refresh_results', {'startedAt': (now - timedelta(hours=2)).isoformat(),
                                                      'finishedAt': (now - timedelta(minutes=5)).isoformat()})
        assert stock_refresh.due(db, now)
        set_setting(db, 'competitor_refresh_results', {'startedAt': (now - timedelta(hours=1)).isoformat()})
        assert not stock_refresh.due(db, now)
        set_setting(db, 'competitor_refresh_run', {'startedAt': now.isoformat(), 'queue': []})
        assert stock_refresh.due(db, now)


def test_fast_pass_withdraws_delayed_stock_without_finishing_discovery(sessions, refresh_config, known_stock, monkeypatch):
    calls = []

    def handle(request):
        calls.append(request)
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /products/')
        if request.url.path == '/products/storage':
            return httpx.Response(200, text=warehouse_page())
        assert request.url.path == '/products/load'
        body = json.loads(request.content)
        assert body['filterManufactor'] == 'neoFroxx', 'Unknown manufacturers stay in the discovery lane'
        return httpx.Response(200, json={'products': [row(16914295, '2028GR100', delayed=True),
                                                     row(16914721, '1779GR100', delayed=False)], 'totalPages': 1})

    monkeypatch.setattr(competitors, 'http_client', lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    discovery = {'startedAt': utcnow().isoformat(), 'queue': [{'s': 'chimmed', 'k': 'start'}]}
    with sessions.begin() as db:
        set_setting(db, 'competitor_run', discovery)
    result = stock_refresh.turn(sessions, seconds=3600)
    assert result and result.get('finishedAt') and result['sources']['chimmed']['withdrawn'] == 1
    assert result['sources']['chimmed']['offers'] == 1
    with sessions() as db:
        bad, good = [db.get(Product, identifier) for identifier in known_stock]
        assert bad and not bad.supplier_stock and good and good.supplier_stock
        assert not db.scalar(select(CompetitorOffer).where(CompetitorOffer.external_id == '16914295'))
        assert get_setting(db, 'competitor_run') == discovery
        assert get_setting(db, 'competitor_refresh_run') is None
        assert not stock_refresh.due(db)
    assert len([request for request in calls if request.url.path == '/products/load']) == 1


def test_refresh_queue_survives_a_worker_turn_and_preserves_unmatched_source_rows(sessions, refresh_config,
                                                                                known_stock, monkeypatch):
    def handle(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        if request.url.path == '/products/storage':
            return httpx.Response(200, text=warehouse_page())
        return httpx.Response(200, json={'products': [row(16914721, '1779GR100', delayed=False)], 'totalPages': 1})

    monkeypatch.setattr(competitors, 'http_client', lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    with sessions.begin() as db:
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'), 'max_pages_per_source': 1})
        competitors.save(db, 'chimmed', [competitors.Offer('unrelated', 'Unknown manufacturer', 'NEW-SKU', 'Review row',
                          competitors.CHIMMED + '/products/storage', pack='5 g')], competitors.Brands(db), utcnow())
    active = stock_refresh.turn(sessions, seconds=3600)
    assert active and len(active['queue']) == 1 and not active.get('finishedAt')
    with sessions() as db:
        assert get_setting(db, 'competitor_refresh_run')['queue'] == active['queue']
    result = stock_refresh.turn(sessions, seconds=3600)
    assert result and result.get('finishedAt')
    with sessions() as db:
        # A partial manufacturer verification must not reconcile other supplier rows as absent.
        assert db.scalar(select(CompetitorOffer).where(CompetitorOffer.external_id == 'unrelated'))


def test_dia_m_only_rechecks_matched_public_urls_and_renews_positive_evidence(sessions, refresh_config, monkeypatch):
    with sessions.begin() as db:
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'), 'sources': ['diam']})
        brand = Brand(name='Merck', slug='merck')
        db.add(brand)
        db.flush()
        public = product(db, brand, 'ABC-100G', packs=('ABC-100G',), default_pack='100 g')
        draft = product(db, brand, 'DRAFT-100G', packs=('DRAFT-100G',), default_pack='100 g')
        draft.status = 'draft'
        offers = [competitors.Offer('existing', 'Merck', 'ABC-100G', 'Public reagent',
                                    'https://www.dia-m.ru/catalog/reactive/public/', pack='100 g'),
                  competitors.Offer('private', 'Merck', 'DRAFT-100G', 'Private reagent',
                                    'https://www.dia-m.ru/catalog/reactive/private/', pack='100 g')]
        before = utcnow() - timedelta(hours=5)
        competitors.save(db, 'diam', offers, competitors.Brands(db), before)
        draft_pack = db.scalar(select(Packaging).where(Packaging.product_id == draft.id))
        assert draft_pack
        db.add(CompetitorOffer(source='diam', external_id='wrong-pack-tie', brand_name='Merck',
                               catalog_number='ABC-100G', catalog_number_norm='abc100g', name='Bad tie',
                               product_id=public.id, packaging_id=draft_pack.id,
                               url='https://www.dia-m.ru/catalog/reactive/wrong-tie/'))
        public_id = public.id
    calls = []

    def handle(request):
        calls.append(request.url.path)
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        assert request.url.path == '/catalog/reactive/public/'
        content = '''<h1>Public reagent <a>Merck</a></h1><table>
        <tr><th>Артикул</th><th>Фасовка</th><th>Наличие на складе</th></tr>
        <tr><td>ABC-100G</td><td>100 г</td><td>В наличии</td></tr></table>
        <a href="/catalog/reactive/discovery/">Unrelated category</a>'''
        return httpx.Response(200, text=content)

    monkeypatch.setattr(competitors, 'http_client', lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    result = stock_refresh.turn(sessions, seconds=3600)
    assert result and result.get('finishedAt') and result['sources']['diam']['pages'] == 1
    with sessions() as db:
        renewed = db.scalar(select(CompetitorOffer).where(CompetitorOffer.product_id == public_id,
                                                        CompetitorOffer.external_id != 'existing'))
        assert renewed and as_utc(renewed.seen_at) > before
        assert get_setting(db, 'competitor_refresh_run') is None
    assert calls == ['/robots.txt', '/catalog/reactive/public/']


def test_disabled_refresh_still_expires_old_evidence_without_network(sessions, refresh_config, known_stock, monkeypatch):
    monkeypatch.setattr(settings, 'competitor_stock_enabled', False)
    with sessions.begin() as db:
        offer = db.scalar(select(CompetitorOffer).where(CompetitorOffer.external_id == '16914295'))
        assert offer
        offer.seen_at = utcnow() - timedelta(hours=7)
    assert stock_refresh.turn(sessions) is None
    with sessions() as db:
        bad = db.get(Product, known_stock[0])
        assert bad and not bad.supplier_stock
        assert db.scalar(select(CompetitorOffer).where(CompetitorOffer.external_id == '16914295'))
