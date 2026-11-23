"""Warehouse category is not inventory: delayed rows must revoke cached stock immediately."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.catalog import competitors
from app.catalog.models import Brand, CompetitorOffer, Packaging, Product, shown_availability
from app.catalog.settings import get_setting, set_setting
from app.catalog.stock_sources.base import Offer, Page
from app.core.db import as_utc, utcnow


def row(**fields):
    return {'id': 16914295, 'name': '2-Nitrophenyl-β-D-Galactopyranoside', 'art_number': '2028GR100',
            'cas': '369-07-3', 'packing': '100 г', 'manufactorName': 'neoFroxx',
            'storage_product': True, 'is_delayed': True, **fields}


def test_actual_customer_case_and_positive_control_have_opposite_inventory():
    page = competitors.chimmed_stock({'products': [row(), row(id=16914721, art_number='1779GR250', cas='5625-37-6', packing='250 г', name='PIPES', is_delayed=False)]})
    assert [offer.external_id for offer in page.offers] == ['16914721']
    assert page.offers[0].quantity is None
    assert page.unavailable_ids == ['16914295']


@pytest.mark.parametrize('status', [None, 'false', '0', [], {}])
def test_unrecognized_delay_status_never_becomes_positive_inventory(status):
    page = competitors.chimmed_stock({'products': [row(is_delayed=status)]})
    assert page.offers == [] and page.incomplete


def product(db):
    brand = Brand(name='neoFroxx', slug='neofroxx')
    db.add(brand)
    db.flush()
    p = Product(brand_id=brand.id, slug='neofroxx-2028gr100', catalog_number='2028GR100',
                catalog_number_norm='2028gr100', name_en='neoFroxx 2028GR100', cas='369-07-3', status='published')
    db.add(p)
    db.flush()
    db.add(Packaging(product_id=p.id, key='100-g', label_ru='100 г', label_en='100 g'))
    db.flush()
    return p


def offer(url=competitors.CHIMMED + '/products/storage'):
    return Offer('16914295', 'neoFroxx', '2028GR100', 'Reference product', url, cas='369-07-3', pack='100 г')


@pytest.mark.parametrize('other_supplier,own_stock', [(False, False), (True, False), (False, True)])
def test_explicit_negative_wins_inside_incomplete_crawl_and_preserves_other_stock(sessions, other_supplier, own_stock):
    with sessions.begin() as db:
        p = product(db)
        brands = competitors.Brands(db)
        competitors.save_page(db, 'chimmed', Page(offers=[offer()]), brands, utcnow())
        assert p.supplier_stock
        if other_supplier:
            competitors.save_page(db, 'skygen', Page(offers=[offer(competitors.SKYGEN + '/catalog/a/')]), brands, utcnow())
        if own_stock:
            p.availability = 'in_stock'
        p.needs_index = False
        # Even a duplicate positive and an incomplete source cannot overrule explicit awaiting-delivery evidence.
        competitors.save_page(db, 'chimmed', Page(offers=[offer()], unavailable_ids=['16914295'],
                                                  incomplete='some other card changed'), brands, utcnow())
        assert not db.scalar(select(CompetitorOffer).where(CompetitorOffer.source == 'chimmed'))
        assert p.supplier_stock is other_supplier
        assert shown_availability(p) == ('in_stock' if own_stock or other_supplier else 'on_order')
        assert p.needs_index or other_supplier


def test_positive_ttl_is_six_hours_but_raw_observations_are_retained_ten_days(sessions):
    now = utcnow()
    with sessions.begin() as db:
        p = product(db)
        set_setting(db, 'competitor_stock', {**get_setting(db, 'competitor_stock'), 'fresh_hours': 6, 'keep_days': 10})
        competitors.save_page(db, 'chimmed', Page(offers=[offer()]), competitors.Brands(db), now - timedelta(hours=7))
        observed = db.scalar(select(CompetitorOffer))
        assert observed is not None and competitors.offer_valid_until(db, observed) == as_utc(observed.seen_at) + timedelta(hours=6)
        assert not list(db.scalars(competitors.fresh_offers(db, now)))
        competitors.settle(db, now, [], now)
        assert db.get(CompetitorOffer, observed.id) is not None
        assert not p.supplier_stock


def test_bad_source_cache_is_quarantined_without_changing_raw_rows_or_other_sources(sessions):
    now = utcnow()
    with sessions.begin() as db:
        p = product(db)
        brands = competitors.Brands(db)
        competitors.save_page(db, 'chimmed', Page(offers=[offer()]), brands, now - timedelta(hours=1))
        competitors.save_page(db, 'skygen', Page(offers=[offer(competitors.SKYGEN + '/catalog/a/')]), brands, now)
        set_setting(db, 'competitor_evidence_since', {'chimmed': now.isoformat()})
        competitors._refresh_flags(db, now)
        old = db.scalar(select(CompetitorOffer).where(CompetitorOffer.source == 'chimmed'))
        assert old and as_utc(old.seen_at) == now - timedelta(hours=1)
        assert competitors.offer_valid_until(db, old) == now
        assert {r.source for r in db.scalars(competitors.fresh_offers(db, now))} == {'skygen'}
        assert p.supplier_stock  # The valid independent supplier still counts.
        competitors.save_page(db, 'chimmed', Page(offers=[offer()]), brands, now + timedelta(seconds=1))
        assert {r.source for r in db.scalars(competitors.fresh_offers(db, now))} == {'chimmed', 'skygen'}
        assert old.id == db.scalar(select(CompetitorOffer.id).where(CompetitorOffer.source == 'chimmed'))
