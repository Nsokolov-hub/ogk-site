"""Legacy quick-cart packaging IDs are accepted narrowly and upgraded to canonical IDs."""

from typing import Any

import pytest
from sqlalchemy import select

from app.catalog.models import Brand, Packaging, Product
from app.catalog.search.query import preview
from app.catalog.stock_availability import resolve_pack
from app.requests.models import SiteRequestItem
from app.requests.schemas import ItemIn
from tests.support import form, submit


def pack():
    return Packaging(id='canonical-pack', product_id='product-1', key='100mg', label_ru='100 мг', label_en='100 mg')


@pytest.mark.parametrize('identifier,label,matched', [
    ('canonical-pack', '100 mg', True),
    ('product-1-100mg', '100 mg', True),
    ('product-1-100mg', '100 мг', True),
    ('product-1-100mg', '5 g', False),
    ('product-1-100mg', '', False),
    ('other-product-100mg', '100 mg', False),
    ('product-1-other-key', '100 mg', False),
])
def test_legacy_synthetic_id_requires_own_product_key_and_matching_label(identifier, label, matched):
    packaging = pack()
    resolved = resolve_pack([packaging], {'site_packaging_id': identifier, 'packaging': label})
    assert (resolved is packaging) is matched


def test_new_search_documents_use_canonical_ids_and_old_ones_keep_the_legacy_id():
    hit: dict[str, Any] = {'id': 'product-1', 'slug': 'product-1', 'brand_slug': 'edqm', 'brand': 'EDQM', 'card_type': 'reference',
           'name': 'Reference', 'catalog_number': 'Y0001897',
           'packagings': [{'id': 'canonical-pack', 'key': '100mg', 'label_ru': '100 мг', 'label_en': '100 mg'}]}
    assert preview(hit, 'ru')['packagings'][0]['id'] == 'canonical-pack'
    hit['packagings'][0].pop('id')
    assert preview(hit, 'ru')['packagings'][0]['id'] == 'product-1-100mg'


def test_full_length_legacy_pack_key_fits_the_public_request_contract():
    packaging = pack()
    packaging.product_id = '5bb31f58-6d00-4000-a000-000000000001'
    packaging.key = 'x' * 80
    identifier = f'{packaging.product_id}-{packaging.key}'
    item = ItemIn.model_validate({'siteProductId': packaging.product_id, 'sitePackagingId': identifier,
                                 'name': 'Reference', 'packaging': '100 mg', 'quantity': 1})
    assert item.site_packaging_id is not None and len(item.site_packaging_id) == 117
    assert resolve_pack([packaging], item.model_dump()) is packaging


def test_accepted_legacy_quick_cart_line_stores_canonical_pack_id(client, sessions):
    with sessions.begin() as db:
        brand = Brand(slug='edqm', name='EDQM')
        db.add(brand)
        db.flush()
        product = Product(id='product-1', brand_id=brand.id, catalog_number='Y0001897',
                          catalog_number_norm='y0001897', slug='edqm-y0001897', name_en='Oxcarbazepine CRS',
                          cas='28721-07-5', status='published')
        db.add(product)
        db.flush()
        db.add(Packaging(id='canonical-pack', product_id=product.id, position=0, key='100mg',
                         label_ru='100 мг', label_en='100 mg', availability='in_stock'))
    body = form()
    body['items'][0].update(siteProductId='product-1', sitePackagingId='product-1-100mg')
    response = submit(client, body)
    assert response.status_code == 201, response.text
    with sessions() as db:
        item = db.scalar(select(SiteRequestItem).where(SiteRequestItem.request_id == response.json()['siteRequestId']))
        assert item.site_packaging_id == 'canonical-pack'
        assert item.stock_snapshot['site_packaging_id'] == 'canonical-pack'
        assert item.stock_snapshot['availability'] == 'in_stock'
