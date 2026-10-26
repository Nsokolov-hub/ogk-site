"""Products (ADM-03), the import wizard (ADM-04) and the queues (ADM-05) of the admin panel."""

from datetime import date

from sqlalchemy import func, select

from app.admin import jobs
from app.admin.models import ImportUpload, ProductDemand
from app.catalog.models import Brand, Document, ImportIssue, Packaging, Product, SearchMiss, SlugRedirect
from app.core.db import utcnow
from tests.catalog.support import assortment


def product_id(db, number: str) -> str:
    return db.scalar(select(Product.id).where(Product.catalog_number == number))


def test_the_list_filters_by_number_brand_category_and_completeness(seeded, signed_in):
    viewer = signed_in('viewer')
    found = viewer.ok(viewer.get('/products', params={'q': 'y0001897'}))
    assert found['total'] == 1 and found['items'][0]['catalogNumber'] == 'Y0001897'
    by_brand = viewer.ok(viewer.get('/products', params={'brand': 'edqm', 'category': 'reference-standards'}))
    assert by_brand['total'] > 0 and all(i['brand'] == 'EDQM' for i in by_brand['items'])
    by_name = viewer.ok(viewer.get('/products', params={'q': 'Oxcarbazepine'}))
    assert by_name['total'] >= 1
    rich = viewer.ok(viewer.get('/products', params={'min_completeness': 70, 'sort': 'completeness'}))
    assert all(i['completeness'] >= 70 for i in rich['items'])
    assert viewer.post('/products/bulk', {'ids': ['x'], 'action': 'reindex'}).status_code == 403


def test_the_editor_saves_a_card_and_protects_hand_made_fields(seeded, signed_in):
    catalog = signed_in('catalog')
    with seeded() as db:
        target = product_id(db, 'Y0001897')
    view = catalog.ok(catalog.get(f'/products/{target}'))
    assert view['brand']['slug'] == 'edqm' and view['data']['categories'][0]['primary'] is True
    data = view['data']
    data['nameEn'] = 'Oxcarbazepine CRS (batch 4)'
    data['purity'] = '≥ 99,5 %'
    data['packagings'] = [{'labelRu': '100 мг', 'labelEn': '', 'availability': 'in_stock'},
                          {'amount': '1', 'unit': 'g', 'labelRu': '', 'labelEn': ''}]
    data['documents'] = [{'type': 'sds', 'lang': 'en', 'titleEn': 'SDS', 'href': 'https://example.com/sds.pdf',
                          'access': 'public'}]
    refused = catalog.put(f'/products/{target}', {'data': data})
    assert refused.status_code == 422 and 'rightsBasis' in refused.json()['field']
    data['documents'][0]['rightsBasis'] = 'Медиакит EDQM, письмо от 01.10.2026'
    saved = catalog.ok(catalog.put(f'/products/{target}', {'data': data}))
    assert 'name_en' in saved['manualFields'] and 'availability' not in saved['manualFields']
    assert saved['history'][0]['action'] == 'update' and 'nameEn' in saved['history'][0]['summary']
    with seeded() as db:
        packs = db.scalars(select(Packaging).where(Packaging.product_id == target).order_by(Packaging.position)).all()
        assert [(p.key, p.label_en, p.availability) for p in packs] == [('100-mg', '100 mg', 'in_stock'),
                                                                        ('1-g', '1 g', 'on_order')]
        assert db.scalar(select(func.count()).select_from(Document).where(Document.product_id == target)) == 1
    bad_cas = catalog.put(f'/products/{target}', {'data': {**saved['data'], 'cas': '28721-07-4'}})
    assert bad_cas.json()['code'] == 'CAS_INVALID'
    restored = catalog.ok(catalog.post(f'/products/{target}/restore/{view["history"][0]["id"]}'
                                       if view['history'] else f'/products/{target}/restore/{saved["history"][0]["id"]}'))
    assert restored['data']['nameEn'] == 'Oxcarbazepine CRS (batch 4)'


def test_a_new_slug_keeps_the_old_address(seeded, signed_in):
    catalog = signed_in('catalog')
    with seeded() as db:
        target = product_id(db, 'Y0001897')
    data = catalog.ok(catalog.get(f'/products/{target}'))['data']
    old = data['slug']
    catalog.ok(catalog.put(f'/products/{target}', {'data': {**data, 'slug': 'edqm-y0001897-oxcarbazepine'}}))
    with seeded() as db:
        assert db.scalar(select(SlugRedirect.old_slug).where(SlugRedirect.target_id == target)) == old


def test_bulk_actions_and_manual_products(seeded, signed_in):
    catalog = signed_in('catalog')
    with seeded() as db:
        ids = list(db.scalars(select(Product.id).where(Product.status == 'published').limit(3)))
        brand = db.scalar(select(Brand.id).where(Brand.slug == 'waters'))
    catalog.ok(catalog.post('/products/bulk', {'ids': ids, 'action': 'status', 'value': 'archived'}))
    catalog.ok(catalog.post('/products/bulk', {'ids': ids, 'action': 'primary_category',
                                               'value': 'chromatography/hplc-columns'}))
    with seeded() as db:
        assert set(db.scalars(select(Product.status).where(Product.id.in_(ids)))) == {'archived'}
        assert not any(db.scalars(select(Product.indexable).where(Product.id.in_(ids))))
    assert catalog.post('/products/bulk', {'ids': ids, 'action': 'status', 'value': 'gone'}).status_code == 422
    created = catalog.ok(catalog.post('/products', {'brandId': brand, 'catalogNumber': '186003034',
                                                    'nameEn': 'XBridge C18 Column, 5 µm, 4.6 x 150 mm',
                                                    'cardType': 'equipment',
                                                    'categoryPath': 'chromatography/hplc-columns'}))
    assert created['data']['status'] == 'draft' and created['source'] == 'manual'
    again = catalog.post('/products', {'brandId': brand, 'catalogNumber': '186-003-034', 'nameEn': 'Duplicate'})
    assert again.status_code == 409


def test_the_import_wizard_previews_runs_and_rolls_back(seeded, signed_in, tmp_path):
    catalog = signed_in('catalog')
    path = assortment(tmp_path / 'Прайс.xlsx', [('Caffeine', 'C-100', '58-08-2', 'Sigma-Aldrich', '100 мг | 1 г'),
                                                ('Thing', 'T-1', '1-1-1', 'Unheard Maker', None)])
    with path.open('rb') as handle:
        upload = catalog.ok(catalog.client.post('/api/v1/admin/import/uploads', headers=catalog.headers,
                                                files={'file': ('Прайс.xlsx', handle)}))
    assert upload['header'][:3] == ['№', 'Наименование', 'Кат. №'] and len(upload['sample']) == 2
    assert upload['suggested'][0]['code'] == 'assortment' and upload['suggested'][0]['complete']
    queued = catalog.ok(catalog.post(f'/import/uploads/{upload["id"]}/run', {'source': 'assortment', 'dryRun': True}))
    assert queued['status'] == 'queued'
    assert catalog.post(f'/import/uploads/{upload["id"]}/run', {'source': 'assortment'}).status_code == 409
    jobs.start_import(upload['id'], 'Сотрудник catalog', seeded, wait=True)
    preview = catalog.ok(catalog.get(f'/import/uploads/{upload["id"]}'))
    assert preview['status'] == 'done' and preview['batch']['dryRun'] is True
    assert preview['batch']['fileName'] == 'Прайс.xlsx' and preview['batch']['author'] == 'Сотрудник catalog'
    with seeded() as db:
        assert db.scalar(select(Product.id).where(Product.catalog_number == 'C-100')) is None
    catalog.ok(catalog.post(f'/import/uploads/{upload["id"]}/run', {'source': 'assortment', 'dryRun': False}))
    jobs.start_import(upload['id'], 'Сотрудник catalog', seeded, wait=True)
    done = catalog.ok(catalog.get(f'/import/uploads/{upload["id"]}'))
    batch = catalog.ok(catalog.get(f'/import/batches/{done["batchId"]}'))
    assert batch['counters']['created'] >= 2 and any(s['code'] == 'BRAND_CREATED' for s in batch['summary'])
    xlsx = catalog.get(f'/import/batches/{done["batchId"]}/issues.xlsx')
    assert xlsx.status_code == 200 and xlsx.content[:2] == b'PK'
    journal = catalog.ok(catalog.get('/import/batches'))
    assert journal['total'] == 2
    assert catalog.ok(catalog.post(f'/import/batches/{done["batchId"]}/rollback'))['deleted'] >= 2
    with seeded() as db:
        assert db.scalar(select(Product.id).where(Product.catalog_number == 'C-100')) is None
        assert db.scalar(select(ImportUpload.status)) == 'done'


def test_saving_a_source_template_needs_the_required_columns(seeded, signed_in):
    catalog = signed_in('catalog')
    sources = catalog.ok(catalog.get('/import/sources'))
    assert {s['code'] for s in sources['items']} >= {'assortment', 'price'}
    refused = catalog.put('/import/sources/price', {'name': 'Прайс', 'mapping': {'name': 'Наименование'}})
    assert refused.status_code == 422
    saved = catalog.ok(catalog.put('/import/sources/supplier-x', {
        'name': 'Поставщик X', 'mapping': {'brand': 'Бренд', 'catalog_number': 'Артикул', 'cas': 'CAS'}}))
    assert saved['mapping']['catalog_number'] == 'Артикул' and saved['builtIn'] is False


def test_queues_conflicts_brands_controlled_demand_and_misses(seeded, signed_in, tmp_path):
    catalog = signed_in('catalog')
    with seeded() as db:
        target = product_id(db, 'Y0001897')
    path = assortment(tmp_path / 'a.xlsx', [('Oxcarbazepine', 'Y0001897', '50-00-0', 'EDQM', '100 мг'),
                                             ('Odd', 'Z-9', None, 'Maker Nobody Knows', None)])
    from app.catalog.importer import run

    run.import_files(seeded, [path], source='assortment')
    queues = catalog.ok(catalog.get('/queues'))
    assert queues['conflicts'] == 1 and queues['brands'] == 1
    conflict = catalog.ok(catalog.get('/queues/conflicts'))['items'][0]
    assert conflict['productId'] == target and conflict['currentCas'] == '28721-07-5'
    catalog.ok(catalog.post(f'/queues/conflicts/{conflict["id"]}', {'action': 'keep'}))
    assert catalog.ok(catalog.get('/queues'))['conflicts'] == 0

    newcomer = catalog.ok(catalog.get('/queues/brands'))['items'][0]
    with seeded() as db:
        waters = db.scalar(select(Brand.id).where(Brand.slug == 'waters'))
    merged = catalog.ok(catalog.post(f'/queues/brands/{newcomer["id"]}', {'action': 'merge', 'targetId': waters}))
    assert merged['moved'] == 1 and catalog.ok(catalog.get('/queues'))['brands'] == 0
    with seeded() as db:
        assert db.scalar(select(func.count()).select_from(ImportIssue).where(
            ImportIssue.code == 'BRAND_CREATED', ImportIssue.resolved.is_(False))) == 0

    with seeded.begin() as db:
        product = db.get(Product, target)
        product.controlled, product.controlled_state = 'pp964', 'review'
        db.add(ProductDemand(product_id=target, day=date.today(), views=5, requests=2))
        db.add(SearchMiss(query='неизвестный стандарт', lang='ru', count=7, last_at=utcnow()))
    assert catalog.ok(catalog.get('/queues/controlled'))['items'][0]['id'] == target
    catalog.ok(catalog.post(f'/queues/controlled/{target}', {'decision': 'cleared'}))
    with seeded() as db:
        assert db.get(Product, target).controlled is None
    assert catalog.ok(catalog.get('/queues/misses'))['items'][0] == {
        'query': 'неизвестный стандарт', 'lang': 'ru', 'count': 7,
        'lastAt': catalog.ok(catalog.get('/queues/misses'))['items'][0]['lastAt']}


def test_card_views_count_towards_the_enrich_queue(seeded, client, signed_in):
    with seeded.begin() as db:
        product = db.scalar(select(Product).where(Product.status == 'published', Product.indexable.is_(False)))
        assert product is not None
        slug, target = product.slug, product.id
    for _ in range(3):
        assert client.post(f'/api/v1/public/products/{slug}/view/').status_code == 204
    catalog = signed_in('catalog')
    queue = catalog.ok(catalog.get('/queues/enrich'))
    assert queue['items'][0]['id'] == target and queue['items'][0]['views'] == 3
