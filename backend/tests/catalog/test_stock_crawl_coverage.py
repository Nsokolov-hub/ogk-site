"""Crawl progress must explain source coverage before a long multi-source run has finished."""

from datetime import timedelta

from app.catalog.models import Brand, CompetitorOffer, Packaging, Product
from app.catalog.settings import set_setting
from app.core.db import utcnow
from app.crm.stock import source_status


def observation(db, key, *, product_id=None, packaging_id=None, days=0):
    db.add(CompetitorOffer(id=key, source='skygen', external_id=key, brand_name='Manufacturer',
                           catalog_number=key, catalog_number_norm=key, name=key, quantity=1,
                           url=f'https://klad.skygen.com/catalog/{key}/',
                           product_id=product_id, packaging_id=packaging_id,
                           seen_at=utcnow() - timedelta(days=days)))


def test_running_source_counters_replace_previous_results_without_claiming_completion(sessions):
    started = utcnow().isoformat()
    previous = (utcnow() - timedelta(days=3)).isoformat()
    with sessions.begin() as db:
        set_setting(db, 'competitor_results', {'finishedAt': previous, 'sources': {
            'skygen': {'pages': 120, 'offers': 247, 'complete': True},
            'chimmed': {'pages': 12, 'offers': 30, 'complete': True}}})
        set_setting(db, 'competitor_run', {'startedAt': started, 'queue': [
            {'s': 'skygen', 'page': 3}, {'s': 'skygen', 'page': 4}], 'stats': {
            'skygen': {'pages': 2, 'offers': 15, 'matched': 1, 'errors': 0, 'truncated': 0}}})
        observation(db, 'unknown-brand')
        observation(db, 'old-stock-list', days=11)
        db.flush()
        sources = {row['id']: row for row in source_status(db)}
    current = sources['skygen']['last_check']
    assert current == {'checked_at': None, 'started_at': started, 'running': True, 'complete': False,
                       'pending_pages': 2, 'pages': 2, 'offers': 15, 'matched': 1, 'errors': 0, 'truncated': 0,
                       'stored_offers': 2, 'fresh_offers': 1, 'exact_packagings': 0, 'pending_review': 2}
    assert sources['chimmed']['last_check']['checked_at'] == previous
    assert sources['chimmed']['last_check']['complete'] is True
    assert sources['diam']['last_check'] is None


def test_exact_packaging_counter_deduplicates_offers_and_rejects_stale_or_mismatched_links(sessions):
    with sessions.begin() as db:
        brand = Brand(id='maker', slug='maker', name='Manufacturer')
        db.add(brand)
        db.flush()
        for key in ('p1', 'p2'):
            db.add(Product(id=key, brand_id=brand.id, slug=key, catalog_number=key,
                           catalog_number_norm=key, name_en=key))
        db.flush()
        for key in ('p1', 'p2'):
            db.add(Packaging(id=f'{key}-pack', product_id=key, key='1g', label_en='1 g', label_ru='1 г'))
        db.flush()
        observation(db, 'first', product_id='p1', packaging_id='p1-pack')
        observation(db, 'duplicate', product_id='p1', packaging_id='p1-pack')
        observation(db, 'wrong-product', product_id='p2', packaging_id='p1-pack')
        observation(db, 'expired', product_id='p2', packaging_id='p2-pack', days=11)
        observation(db, 'product-only', product_id='p2')
        db.flush()
        source = next(row for row in source_status(db) if row['id'] == 'skygen')
    assert source['last_check'] == {'stored_offers': 5, 'fresh_offers': 4,
                                    'exact_packagings': 1, 'pending_review': 1}


def test_refresh_progress_does_not_replace_catalogue_coverage_or_claim_full_warehouse_verification(sessions):
    started = utcnow().isoformat()
    previous = (utcnow() - timedelta(days=1)).isoformat()
    with sessions.begin() as db:
        set_setting(db, 'competitor_results', {'finishedAt': previous, 'sources': {
            'chimmed': {'pages': 2029, 'offers': 18800, 'complete': False}}})
        set_setting(db, 'competitor_refresh_results', {'startedAt': previous, 'finishedAt': previous,
            'sources': {'chimmed': {'pages': 75, 'offers': 40, 'withdrawn': 15, 'complete': True},
                        'diam': {'pages': 7, 'offers': 8, 'complete': True}}})
        set_setting(db, 'competitor_refresh_run', {'startedAt': started,
            'queue': [{'s': 'chimmed', 'page': 3}],
            'stats': {'chimmed': {'pages': 2, 'offers': 5, 'withdrawn': 15, 'errors': 0}}})
        sources = {entry['id']: entry['last_check'] for entry in source_status(db)}
    full = sources['chimmed']
    assert full['pages'] == 2029 and full['offers'] == 18800 and full['checked_at'] == previous
    assert not full['complete']
    refresh = full['refresh']
    assert refresh == {'pages': 2, 'offers': 5, 'withdrawn': 15, 'errors': 0, 'checked_at': None,
                       'started_at': started, 'running': True, 'complete': False, 'pending_pages': 1,
                       'scope': 'known_stock', 'interval_hours': 2, 'fresh_hours': 6}
    assert sources['diam']['refresh']['running'] is False
    assert sources['diam']['refresh']['checked_at'] == previous
    assert sources['diam']['refresh']['scope'] == 'known_stock'
    assert sources['skygen'] is None
