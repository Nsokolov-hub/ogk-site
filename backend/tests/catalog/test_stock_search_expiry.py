"""Stale index documents cannot advertise supplier stock after its evidence has expired."""

from datetime import timedelta

import pytest

from app.catalog.models import Brand, Product
from app.catalog.search.documents import Context, build
from app.catalog.search.query import preview
from app.core.db import utcnow


def hit(**changes):
    return {'id': 'product', 'slug': 'product', 'card_type': 'standard', 'name': 'Product',
            'brand': 'Brand', 'brand_slug': 'brand', 'catalog_number': 'SKU',
            'availability': 'in_stock', 'stock': 'supplier', **changes}


@pytest.mark.parametrize('deadline', [None, 'invalid'])
def test_legacy_or_invalid_supplier_deadline_is_conservative(deadline):
    assert preview(hit(stock_valid_until=deadline), 'ru')['availability'] == 'on_order'


def test_preview_checks_deadline_even_without_worker_reindexing():
    now = utcnow()
    assert preview(hit(stock_valid_until=(now - timedelta(seconds=1)).isoformat()), 'ru')['availability'] == 'on_order'
    assert preview(hit(stock_valid_until=(now + timedelta(hours=1)).isoformat()), 'ru')['availability'] == 'in_stock'
    assert preview(hit(stock='own', stock_valid_until=(now - timedelta(days=20)).isoformat()), 'ru')['availability'] == 'in_stock'


def test_documents_do_not_keep_raw_expired_supplier_flags(sessions):
    with sessions.begin() as db:
        brand = Brand(slug='brand', name='Brand')
        db.add(brand)
        db.flush()
        product = Product(brand_id=brand.id, catalog_number='SKU', catalog_number_norm='sku', slug='product',
                          name_en='Product', status='published', supplier_stock=True,
                          supplier_stock_until=utcnow() - timedelta(seconds=1))
        db.add(product)
        db.flush()
        docs, _ = build(db, [product], Context(db, False))
        assert docs[0]['availability'] == 'on_order'
        assert docs[0]['stock'] is None
        assert docs[0]['stock_valid_until'] is None
