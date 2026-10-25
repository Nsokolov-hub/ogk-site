"""Pages read from PostgreSQL: product, substance, brand, tree, Sitemap, feed, the cart and old addresses."""

from sqlalchemy import select

from app.catalog.models import Product, Substance
from app.catalog.service import change_slug

URL = '/api/v1/public'


def test_product_page_with_neighbours(client, seeded):
    page = client.get(f'{URL}/products/edqm-y0001897-oxcarbazepine-crs').json()
    product = page['product']
    assert (product['catalogNumber'], product['brand']['name'], product['cas']) == ('Y0001897', 'EDQM', '28721-07-5')
    assert product['texts']['ru']['description'] and product['uniqueDescription'] is True
    assert [c['href'] for c in page['categories']] == ['/catalog/reference-standards/',
                                                      '/catalog/reference-standards/edqm/']
    assert page['substance']['slug'] == 'oxcarbazepine' and page['sameSubstanceTotal'] >= 3
    assert all(p['brand']['slug'] != 'edqm' for p in page['analogues'])
    assert product['packagings'][0]['label'] == '100 мг'
    english = client.get(f'{URL}/products/edqm-y0001897-oxcarbazepine-crs', params={'lang': 'en'}).json()
    assert english['product']['packagings'][0]['label'] == '100 mg'


def test_columns_get_analogues_and_guard_columns(client, seeded):
    with seeded() as db:
        slug = db.scalar(select(Product.slug).where(Product.catalog_number == '186003116'))
    page = client.get(f'{URL}/products/{slug}').json()
    assert page['product']['cardType'] == 'equipment'
    assert page['accessories'], 'a column offers guard columns and filters'


def test_changed_address_answers_with_the_new_one(client, seeded):
    with seeded.begin() as db:
        product = db.scalar(select(Product).where(Product.catalog_number == 'Y0001897'))
        change_slug(db, 'product', product.id, product.slug, 'edqm-y0001897-oxcarbazepine-crs-ph-eur')
        product.slug = 'edqm-y0001897-oxcarbazepine-crs-ph-eur'
    moved = client.get(f'{URL}/products/edqm-y0001897-oxcarbazepine-crs').json()
    assert moved['moved'] == 'edqm-y0001897-oxcarbazepine-crs-ph-eur' and moved['product'] is None
    assert client.get(f'{URL}/products/no-such-product').status_code == 404


def test_controlled_products_have_no_pages(client, seeded):
    with seeded() as db:
        slug = db.scalar(select(Product.slug).where(Product.controlled.is_not(None)))
    assert client.get(f'{URL}/products/{slug}').status_code == 404


def test_tree_brands_substances_and_categories(client, seeded):
    tree = client.get(f'{URL}/catalog/tree').json()
    standards = next(c for c in tree if c['slug'] == 'reference-standards')
    assert standards['nameEn'] == 'Reference standards' and standards['hasEn'] is True
    assert [c['slug'] for c in standards['children']][:2] == ['edqm', 'usp']
    category = client.get(f'{URL}/catalog/category', params={'path': 'reference-standards/edqm'}).json()
    assert category['content']['ru']['h1'] and 'brand' in category['facets']
    assert client.get(f'{URL}/catalog/category', params={'path': 'nope'}).status_code == 404
    brands = client.get(f'{URL}/brands').json()
    assert brands[0]['slug'] == 'edqm' and brands[0]['count'] > 0 and brands[0]['content']['ru']['intro']
    brand = client.get(f'{URL}/brands/waters').json()
    assert brand['products'] and brand['categories'][0]['slug'].startswith('chromatography')
    substances = client.get(f'{URL}/substances').json()
    assert any(s['slug'] == 'oxcarbazepine' and s['count'] >= 3 for s in substances)
    with seeded() as db:
        assert db.scalar(select(Substance).where(Substance.slug == 'oxcarbazepine'))
    page = client.get(f'{URL}/substances/oxcarbazepine').json()
    assert page['items'][0]['substance']['role'] == 'api'


def test_sitemap_lists_only_indexable_cards_and_feed_skips_controlled(client, seeded):
    sitemap = client.get(f'{URL}/catalog/sitemap').json()
    with seeded() as db:
        indexable = set(db.scalars(select(Product.slug).where(Product.indexable.is_(True))))
        controlled = set(db.scalars(select(Product.id).where(Product.controlled.is_not(None))))
    assert {i['slug'] for i in sitemap['items']} == indexable and sitemap['total'] == len(indexable)
    feed = client.get(f'{URL}/catalog/feed').json()
    assert feed['items'] and not controlled & {i['id'] for i in feed['items']}
    assert all(not i['categorySlug'].startswith('laboratory-glassware') for i in feed['items'])


def test_guest_cart_by_cookie(client):
    assert client.get(f'{URL}/cart').json() == {'items': [], 'updatedAt': None}
    saved = client.put(f'{URL}/cart', json={'items': [{'key': 'p1:100-mg', 'quantity': 2}]})
    assert saved.status_code == 200 and saved.cookies.get('ogk_cart')
    assert client.get(f'{URL}/cart').json()['items'] == [{'key': 'p1:100-mg', 'quantity': 2}]
    client.cookies.clear()
    assert client.get(f'{URL}/cart').json()['items'] == []
    too_many = client.put(f'{URL}/cart', json={'items': [{'key': str(i)} for i in range(201)]})
    assert too_many.status_code == 422
