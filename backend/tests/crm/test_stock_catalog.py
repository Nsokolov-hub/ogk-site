"""The CRM sees exact fresh stock privately, with a separate manager review queue."""

import hashlib
import hmac
import json
import time
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.catalog.identity import ALIASES, CHANNEL_SLUG, MASTER_SLUG, REVIEW, SOURCE_URL
from app.catalog.models import Brand, Category, CompetitorOffer, Packaging, Product, ProductCategory
from app.catalog.normalize import compact
from app.catalog.settings import set_setting
from app.catalog.stock_availability import capture_stock
from app.core.config import settings
from app.core.db import utcnow
from app.main import app

URL = '/api/v1/crm/stock'
SECRET = 'stock-test-secret'


@pytest.fixture(autouse=True)
def link(monkeypatch):
    monkeypatch.setattr(settings, 'crm_events_secret', SECRET)
    monkeypatch.setattr(settings, 'crm_events_allowed_ips', '')


def ask(client, body=None, *, secret=SECRET, stamp=None):
    raw = json.dumps(body or {}, ensure_ascii=False).encode()
    moment = str(int(time.time()) if stamp is None else stamp)
    signature = 'sha256=' + hmac.new(secret.encode(), moment.encode() + b'.' + raw, hashlib.sha256).hexdigest()
    return client.post(URL, content=raw, headers={'Content-Type': 'application/json', 'X-CRM-Timestamp': moment,
                                                 'X-CRM-Signature': signature})


def product(db, identifier, *, status='published', controlled=None, own=False, packs=1, slug=None, brand=None):
    if brand is None:
        brand = db.get(Brand, 'test-brand')
        if brand is None:
            brand = Brand(id='test-brand', slug='test-brand', name='Test manufacturer')
            db.add(brand)
            db.flush()
    row = Product(id=identifier, brand_id=brand.id, catalog_number=f'SKU-{identifier}',
                  catalog_number_norm=compact(f'SKU-{identifier}'), slug=slug or identifier,
                  name_en=f'Test {identifier}', status=status, controlled=controlled,
                  availability='in_stock' if own else 'on_order')
    db.add(row)
    db.flush()
    packaging = []
    for position in range(packs):
        pack = Packaging(id=f'{identifier}-pack-{position}', product_id=row.id, position=position,
                         key=f'{position + 1}g', label_ru=f'{position + 1} г', label_en=f'{position + 1} g',
                         catalog_number=f'{row.catalog_number}-{position + 1}G')
        db.add(pack)
        packaging.append(pack)
    db.flush()
    return row, packaging


def offer(db, identifier, row, pack, now, *, source='chimmed', days=0, quantity=None, updated_days=None):
    observed = now - timedelta(days=days)
    value = CompetitorOffer(id=identifier, source=source, external_id=identifier,
                            brand_name='Test manufacturer', catalog_number='Supplier SKU',
                            catalog_number_norm='suppliersku', name='Supplier product', pack='1 g',
                            product_id=row.id if row else None, packaging_id=pack.id if pack else None,
                            url=f'https://supplier.test/{identifier}', quantity=quantity, price='PRIVATE PRICE',
                            seen_at=observed,
                            stock_updated_at=now - timedelta(days=updated_days) if updated_days is not None else None)
    db.add(value)
    db.flush()
    return value


def test_stock_requires_existing_hmac_channel_and_is_absent_from_public_schema(client, monkeypatch):
    assert URL not in app.openapi()['paths']
    assert client.get(URL).status_code == 405
    assert client.post(URL, json={}).status_code == 401
    assert ask(client, secret='wrong').status_code == 401
    assert ask(client, stamp=int(time.time()) - 301).json()['code'] == 'CRM_SIGNATURE_EXPIRED'
    monkeypatch.setattr(settings, 'crm_events_allowed_ips', '10.0.0.0/8')
    assert ask(client).status_code == 403
    monkeypatch.setattr(settings, 'crm_events_allowed_ips', '')
    monkeypatch.setattr(settings, 'crm_events_secret', '')
    assert ask(client).status_code == 503


@pytest.mark.parametrize('body', [{'limit': 201}, {'mode': 'publish'}, {'price': True}, {'q': 'x' * 201}])
def test_bad_catalog_queries_are_refused(client, body):
    assert ask(client, body).json()['code'] == 'CRM_REQUEST_INVALID'


def test_only_exact_fresh_public_pack_rows_are_listed_once_and_prices_stay_private(client, sessions):
    now = utcnow()
    with sessions.begin() as db:
        set_setting(db, 'hide_controlled', True)
        public, packs = product(db, 'public')
        offer(db, 'chimmed-good', public, packs[0], now)
        offer(db, 'skygen-good', public, packs[0], now, source='skygen', quantity=3)
        offer(db, 'sold-out', public, packs[0], now, quantity=0)
        offer(db, 'stale-observation', public, packs[0], now, days=11)
        offer(db, 'stale-stock-date', public, packs[0], now, updated_days=11)
        offer(db, 'product-only', public, None, now)
        for identifier, values in [('draft', {'status': 'draft'}), ('controlled', {'controlled': 'PKU'}),
                                   ('hidden', {})]:
            row, pack = product(db, identifier, **values)
            offer(db, f'{identifier}-offer', row, pack[0], now)
            if identifier == 'hidden':
                category = Category(slug='hidden', path='hidden/root/leaf', name_ru='Скрытая')
                db.add(category)
                db.flush()
                db.add(ProductCategory(product_id=row.id, category_id=category.id))
                set_setting(db, 'hidden_categories', ['hidden/root'])
        other, _ = product(db, 'other')
        # A historic inconsistent tie must not contaminate another product's evidence.
        offer(db, 'wrong-product-tie', other, packs[0], now)
    answer = ask(client)
    assert answer.status_code == 200, answer.text
    rows = answer.json()['items']
    assert len(rows) == 1 and rows[0]['product_id'] == 'public'
    assert {value['offer_id'] for value in rows[0]['offers']} == {'chimmed-good', 'skygen-good'}
    assert rows[0]['origin'] == 'supplier'
    assert 'PRIVATE PRICE' not in answer.text and '"price"' not in answer.text
    only_skygen = ask(client, {'source': 'skygen'}).json()['items']
    assert len(only_skygen) == 1 and {o['source'] for o in only_skygen[0]['offers']} == {'skygen'}


def test_own_stock_requires_the_selected_pack_or_one_pack_product(client, sessions):
    with sessions.begin() as db:
        product(db, 'own-one', own=True)
        row, packs = product(db, 'own-many', own=True, packs=2)
        packs[1].availability = 'in_stock'
        product(db, 'own-none', own=True, packs=0)
    rows = ask(client).json()['items']
    assert {row['packaging_id'] for row in rows} == {'own-one-pack-0', 'own-many-pack-1'}
    assert all(row['origin'] == 'own' for row in rows)
    assert ask(client, {'source': 'chimmed'}).json()['items'] == []


def test_overlapping_stock_sources_are_deduplicated_before_filters_and_pagination(client, sessions):
    now = utcnow()
    with sessions.begin() as db:
        both, packs = product(db, 'a-overlap', own=True)
        packs[0].availability = 'in_stock'
        offer(db, 'overlap-chimmed', both, packs[0], now)
        offer(db, 'overlap-skygen', both, packs[0], now, source='skygen')
        _, explicit = product(db, 'b-explicit', packs=2)
        explicit[1].availability = 'in_stock'
        product(db, 'c-own', own=True)
    first = ask(client, {'limit': 1}).json()
    second = ask(client, {'limit': 1, 'as_of': first['as_of'], 'cursor': first['next_cursor']}).json()
    third = ask(client, {'limit': 1, 'as_of': first['as_of'], 'cursor': second['next_cursor']}).json()
    assert [page['items'][0]['packaging_id'] for page in (first, second, third)] == [
        'a-overlap-pack-0', 'b-explicit-pack-1', 'c-own-pack-0']
    assert first['has_more'] and second['has_more'] and not third['has_more']
    assert len(first['items'][0]['offers']) == 2
    filtered = ask(client, {'q': 'SKU-b-explicit-2G', 'brand': 'Test manufacturer', 'limit': 1}).json()
    assert [row['packaging_id'] for row in filtered['items']] == ['b-explicit-pack-1']
    assert not filtered['has_more']
    source = ask(client, {'source': 'chimmed', 'limit': 1}).json()
    assert [row['packaging_id'] for row in source['items']] == ['a-overlap-pack-0']
    assert [value['source'] for value in source['items'][0]['offers']] == ['chimmed']
    assert not source['has_more']


def test_catalog_cursor_is_keyset_and_bound_to_filters_and_as_of(client, sessions):
    with sessions.begin() as db:
        for identifier in ('row-a', 'row-b', 'row-c'):
            product(db, identifier, own=True)
    first = ask(client, {'limit': 1, 'q': 'Test'}).json()
    assert first['has_more'] and first['next_cursor']
    body = {'limit': 1, 'q': 'Test', 'as_of': first['as_of'], 'cursor': first['next_cursor']}
    second = ask(client, body).json()
    third = ask(client, {**body, 'cursor': second['next_cursor']}).json()
    assert [first['items'][0]['product_id'], second['items'][0]['product_id'], third['items'][0]['product_id']] == [
        'row-a', 'row-b', 'row-c']
    assert third['has_more'] is False and third['next_cursor'] is None
    for change in ({'q': ''}, {'source': 'skygen'}, {'brand': 'other'}, {'mode': 'review'},
                   {'as_of': (utcnow() - timedelta(minutes=1)).isoformat()}, {'cursor': 'invalid'}):
        response = ask(client, {**body, **change})
        assert response.status_code == 422 and response.json()['code'] == 'STOCK_CURSOR_INVALID'
    expired = ask(client, {'as_of': (utcnow() - timedelta(hours=2)).isoformat()})
    assert expired.json()['code'] == 'STOCK_VIEW_EXPIRED'


def test_backdated_as_of_does_not_resurrect_expired_stock(client, sessions):
    now = utcnow()
    with sessions.begin() as db:
        row, packs = product(db, 'expired')
        offer(db, 'just-expired', row, packs[0], now - timedelta(minutes=1), days=10)
    assert ask(client, {'as_of': (now - timedelta(minutes=30)).isoformat()}).json()['items'] == []


def test_maximum_unicode_filters_fit_the_next_page_cursor(client, sessions):
    query, manufacturer = '名' * 200, '牌' * 200
    with sessions.begin() as db:
        brand = Brand(slug='long-brand', name=manufacturer)
        db.add(brand)
        db.flush()
        for identifier in ('long-a', 'long-b'):
            row, _ = product(db, identifier, own=True, brand=brand)
            row.name_en = query + ' ' + identifier
    first = ask(client, {'q': query, 'brand': manufacturer, 'limit': 1}).json()
    assert first['has_more'] and len(first['next_cursor']) > 1200
    second = ask(client, {'q': query, 'brand': manufacturer, 'limit': 1,
                          'as_of': first['as_of'], 'cursor': first['next_cursor']})
    assert second.status_code == 200, second.text
    assert second.json()['items'][0]['product_id'] == 'long-b'


def test_unmatched_review_is_explicitly_unknown_and_can_show_stale_hints(client, sessions):
    now = utcnow()
    with sessions.begin() as db:
        offer(db, 'unmatched-fresh', None, None, now)
        offer(db, 'unmatched-stale', None, None, now, days=11)
        before = db.scalar(select(func.count()).select_from(Product))
    answer = ask(client, {'mode': 'review'}).json()
    assert {row['id']: row['fresh'] for row in answer['items']} == {
        'unmatched-fresh': True, 'unmatched-stale': False}
    assert all(row['availability'] == 'unknown' and row['product_url'] is None for row in answer['items'])
    assert all('Автоматическая публикация отключена' in row['reason'] for row in answer['items'])
    first = ask(client, {'mode': 'review', 'limit': 1}).json()
    second = ask(client, {'mode': 'review', 'limit': 1, 'as_of': first['as_of'],
                          'cursor': first['next_cursor']}).json()
    assert {first['items'][0]['id'], second['items'][0]['id']} == {'unmatched-fresh', 'unmatched-stale'}
    assert second['has_more'] is False
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == before


def test_source_status_uses_real_runner_results_and_merged_source_metadata(client, sessions):
    checked = utcnow().isoformat()
    with sessions.begin() as db:
        set_setting(db, 'competitor_results', {'finishedAt': checked,
                    'sources': {'chimmed': {'offers': 4, 'complete': True, 'refused': None}}})
    sources = {row['id']: row for row in ask(client).json()['sources']}
    assert sources['chimmed']['status'] == 'supported'
    assert sources['chimmed']['last_check'] == {'checked_at': checked, 'offers': 4, 'complete': True, 'refused': None,
                                               'stored_offers': 0, 'fresh_offers': 0,
                                               'exact_packagings': 0, 'pending_review': 0}
    assert 'laverna' in sources and sources['laverna']['last_check'] is None


def test_capture_refuses_identity_mismatch_custom_pack_and_hidden_products(sessions):
    now = utcnow()
    with sessions.begin() as db:
        row, packs = product(db, 'capture', own=True)
        good = {'site_product_id': row.id, 'site_packaging_id': packs[0].id, 'brand': 'Test manufacturer',
                'catalog_number': row.catalog_number, 'packaging': '1 g', 'cas': None}
        assert capture_stock(db, good, now)['availability'] == 'in_stock'
        for change in ({'brand': 'Another manufacturer'}, {'brand': 'USP'}, {'catalog_number': 'Other SKU'},
                       {'site_packaging_id': 'foreign-pack'}, {'packaging': '2 g'}, {'custom_packaging': True}):
            assert capture_stock(db, {**good, **change}, now)['availability'] == 'unknown'
        category = Category(slug='hidden', path='hidden', name_ru='Скрытая')
        db.add(category)
        db.flush()
        db.add(ProductCategory(product_id=row.id, category_id=category.id))
        db.flush()
        set_setting(db, 'hidden_categories', ['hidden'])
        assert capture_stock(db, good, now)['availability'] == 'unknown'


def test_reviewed_identity_keeps_canonical_list_and_approved_pack_allowlist(client, sessions):
    with sessions.begin() as db:
        master, packs = product(db, 'master', slug=MASTER_SLUG, own=True, packs=2)
        channel, channel_packs = product(db, 'channel', slug=CHANNEL_SLUG, own=True, packs=2)
        for row, row_packs in ((master, packs), (channel, channel_packs)):
            row.seo = {'identity': {'review': REVIEW, 'sourceUrl': SOURCE_URL, 'manufacturer': 'USP',
                       'canonicalSlug': MASTER_SLUG, 'canonicalProductId': master.id,
                       'identifierAliases': ALIASES, 'verifiedPackagingId': row_packs[1].id}}
        db.flush()
        item = {'site_product_id': channel.id, 'site_packaging_id': channel_packs[1].id,
                'brand': 'USP', 'catalog_number': channel.catalog_number, 'packaging': '2 g'}
        assert capture_stock(db, item)['availability'] == 'in_stock'
        assert capture_stock(db, {**item, 'site_packaging_id': channel_packs[0].id,
                                  'packaging': '1 g'})['availability'] == 'unknown'
    rows = ask(client).json()['items']
    assert [(row['product_id'], row['packaging_id'], row['manufacturer']) for row in rows] == [
        ('master', 'master-pack-1', 'USP')]
