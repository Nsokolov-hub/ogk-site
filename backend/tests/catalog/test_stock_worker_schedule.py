"""Published-stock refreshes progress continuously without starving discovery, delivery or indexing."""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select, update

from app.catalog import competitors, stock_refresh
from app.catalog.models import Brand, CompetitorOffer, Packaging, Product
from app.core import storefront
from app.core.config import settings
from app.core.db import utcnow
from app.outbox import worker


@pytest.fixture
def stock_worker(sessions, monkeypatch):
    events = []
    monkeypatch.setattr(worker, 'SessionLocal', sessions)
    monkeypatch.setattr(worker, '_stock_turns', 0)
    monkeypatch.setattr(settings, 'competitor_stock_enabled', True)
    monkeypatch.setattr(worker, 'ensure_site_content', lambda: None)
    monkeypatch.setattr(worker, 'ensure_search_index', lambda: None)

    def outbox(db):
        events.append('customer outbox')
        return {'succeeded': 1}

    def refresh(sessions, *, seconds):
        assert seconds == 20
        events.append('refresh')
        return {'queue': ['next page']}

    def discovery(sessions):
        events.append('discovery')
        return {'queue': ['next page']}

    def structures():
        events.append('structures')
        return 0

    def index():
        events.append('index')
        return 1

    monkeypatch.setattr(worker, 'process_events', outbox)
    monkeypatch.setattr(worker, 'draw_structures', structures)
    monkeypatch.setattr(worker, 'index_catalog', index)
    monkeypatch.setattr(stock_refresh, 'turn', refresh)
    monkeypatch.setattr(competitors, 'turn', discovery)
    monkeypatch.setattr(stock_refresh, 'due', lambda db: True)
    monkeypatch.setattr(competitors, 'active', lambda db: True, raising=False)
    monkeypatch.setattr(competitors, 'due', lambda db: True)
    return events


def test_continuous_refresh_reserves_discovery_and_delivers_before_each_crawl(stock_worker):
    # Only the first iteration of a minute runs housekeeping in production. The other iterations must still
    # advance the two stock queues, deliver accepted customer requests and index each changed stock batch.
    for _ in range(8):
        result = worker.run_once(housekeeping=False)
        assert result['succeeded'] == 1 and result['indexed'] == 1
    expected = ['refresh', 'refresh', 'refresh', 'discovery'] * 2
    assert stock_worker == [event for lane in expected
                            for event in ('customer outbox', lane, 'structures', 'index')]


def test_idle_iterations_do_not_start_or_reconcile_supplier_crawls(stock_worker, monkeypatch):
    monkeypatch.setattr(stock_refresh, 'due', lambda db: False)
    monkeypatch.setattr(competitors, 'active', lambda db: False)
    schedule_checks = []

    def scheduled(db):
        schedule_checks.append(True)
        return True

    monkeypatch.setattr(competitors, 'due', scheduled)
    worker.run_once(housekeeping=False)
    assert stock_worker == ['customer outbox', 'structures', 'index']
    assert not schedule_checks


def test_supplier_refresh_failure_preserves_delivery_and_indexing(stock_worker, monkeypatch, caplog):
    def failed(sessions, *, seconds):
        stock_worker.append('failed refresh')
        raise TimeoutError('Supplier timed out')

    monkeypatch.setattr(stock_refresh, 'turn', failed)
    worker.run_once(housekeeping=False)
    assert stock_worker == ['customer outbox', 'failed refresh', 'structures', 'index']
    assert 'competitor_refresh_failed' in caplog.text


def test_housekeeping_still_expires_evidence_when_collection_is_disabled(sessions, monkeypatch):
    monkeypatch.setattr(worker, 'SessionLocal', sessions)
    with sessions.begin() as db:
        brand = Brand(name='Agilent', slug='agilent')
        db.add(brand)
        db.flush()
        product = Product(brand_id=brand.id, slug='worker-expired-stock', catalog_number='SKU1',
                          catalog_number_norm='sku1', name_en='Product', status='published')
        db.add(product)
        db.flush()
        db.add(Packaging(product_id=product.id, position=0, key='1-g', label_en='1 g', label_ru='1 г',
                         catalog_number='SKU1', catalog_number_norm='sku1'))
        db.flush()
        offer = competitors.Offer('expired', 'Agilent', 'SKU1', 'Product', competitors.CHIMMED + '/products/storage',
                                  pack='1 g', quantity=1)
        competitors.save(db, 'chimmed', [offer], competitors.Brands(db), utcnow())
        assert product.supplier_stock
        db.execute(update(CompetitorOffer).values(seen_at=utcnow() - timedelta(days=20)))
    monkeypatch.setattr(settings, 'competitor_stock_enabled', False)
    worker.check_stock_turn(housekeeping=True)
    with sessions() as db:
        assert not db.scalar(select(Product.supplier_stock))
        assert db.scalar(select(Product.needs_index))
        assert db.scalar(select(CompetitorOffer.id)) is None


def test_mass_stock_correction_invalidates_every_product_within_the_web_tag_limit(monkeypatch):
    monkeypatch.setattr(settings, 'web_url', 'https://storefront.test')
    monkeypatch.setattr(settings, 'revalidate_secret', 'test-revalidate-secret')
    calls = []

    def post(url, **kwargs):
        assert url == 'https://storefront.test/api/revalidate/'
        tags = kwargs['json']['tags']
        assert 'catalog' in tags and len(tags) <= storefront.MAX_TAGS
        calls.append(tags)
        return httpx.Response(200)

    monkeypatch.setattr(storefront.httpx, 'post', post)
    slugs = [f'corrected-stock-{index}' for index in range(2005)]
    worker.revalidate_pages(slugs)
    sent = {tag for batch in calls for tag in batch if tag.startswith('product:')}
    assert sent == {f'product:{slug}' for slug in slugs}
