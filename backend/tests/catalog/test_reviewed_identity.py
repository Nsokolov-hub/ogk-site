"""Reviewed SKU migration: exact packaging, no catalog merge and immutable historical requests."""

import argparse
import json
from copy import deepcopy
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.admin.models import AuditEntry
from app.catalog import cli, identity, pilot
from app.catalog.importer import run
from app.catalog.models import Brand, Document, Packaging, Product
from app.catalog.normalize import compact
from app.catalog.search import documents, indexer, query
from app.catalog.search.engine import Result
from app.catalog.settings import get_setting
from app.core import storefront
from app.crm.client import payload
from app.requests.models import SiteRequest
from tests.catalog.support import FakeEngine, assortment
from tests.support import form, submit


@pytest.fixture
def reviewed(sessions):
    with sessions.begin() as db:
        usp = Brand(slug='usp', name='USP')
        sigma = Brand(slug='sigma-aldrich', name='Sigma-Aldrich')
        db.add_all([usp, sigma])
        db.flush()
        rows = []
        for brand, slug, number in ((usp, identity.MASTER_SLUG, '1235831'),
                                     (sigma, identity.CHANNEL_SLUG, '1235831-1AMP')):
            product = Product(brand_id=brand.id, slug=slug, catalog_number=number,
                              catalog_number_norm=compact(number), name_en='Old Enoxaparin label',
                              status='published', source='import:assortment', availability='in_stock',
                              supplier_stock=True, storage='cold', texts={'en': {'description': ['Existing text']}},
                              seo={'ru': {'description': 'Existing metadata'}})
            db.add(product)
            db.flush()
            pack = Packaging(product_id=product.id, key='1-vial', amount=Decimal(1), unit='vial',
                             label_ru='1 фл.', label_en='1 vial', catalog_number='1235831-1AMP',
                             catalog_number_norm=compact('1235831-1AMP'), availability='in_stock',
                             price_estimate=Decimal('543.21'), crm_packing_id='existing-crm-pack')
            db.add_all([pack, Document(product_id=product.id, type='sds', href='/existing-sds.pdf')])
            db.flush()
            rows.append((product.id, pack.id))
    return rows


@pytest.fixture
def production_placeholders(sessions):
    with sessions.begin() as db:
        usp = Brand(slug='usp', name='USP')
        sigma = Brand(slug='sigma-aldrich', name='Sigma-Aldrich')
        db.add_all([usp, sigma])
        db.flush()
        master = Product(id=identity.LEGACY_MASTER_ID, brand_id=usp.id, slug=identity.MASTER_SLUG,
                         name_en='USP 1235831', catalog_number='1235831', catalog_number_norm='1235831',
                         source='import:assortment', status='published', availability='in_stock', supplier_stock=True)
        channel = Product(id='525369d2-db22-4a5d-98be-c803a736bddf', brand_id=sigma.id, slug=identity.CHANNEL_SLUG,
                          name_en='Old channel label', catalog_number='1235831-1AMP',
                          catalog_number_norm=compact('1235831-1AMP'), source='import:assortment', status='published')
        db.add_all([master, channel])
        db.flush()
        pcs = Packaging(product_id=master.id, key='1-pcs', amount=Decimal(1), unit='pcs',
                        label_ru='1 шт.', label_en='1 pcs', availability='in_stock')
        vial = Packaging(product_id=master.id, key='1viala', label_ru='1 виала', label_en='1 vial',
                         availability='in_stock', price_estimate=Decimal('543.21'), crm_packing_id='old-pack-link')
        db.add_all([pcs, vial])
        db.flush()
        return {'master': master.id, 'channel': channel.id, 'pcs': pcs.id, 'vial': vial.id}


def test_dry_run_apply_is_idempotent_and_preserves_catalog_and_old_request(client, sessions, reviewed):
    old = form(items=[{'siteProductId': reviewed[1][0], 'brand': 'Sigma-Aldrich',
                      'catalogNumber': '1235831-1AMP', 'name': 'Old customer label', 'packaging': '1 vial',
                      'quantity': 9, 'unit': 'pack', 'analogue': 'none', 'customPackaging': False}])
    response = submit(client, old)
    assert response.status_code in (200, 201), response.text
    with sessions.begin() as db:
        request = db.scalar(select(SiteRequest))
        old_body = deepcopy(payload(db, request)[0])
        before = {p.id: (p.slug, p.brand_id, p.cas, p.availability, p.supplier_stock, p.storage,
                          deepcopy(p.texts), p.version) for p in db.scalars(select(Product))}
        dry = identity.enrich_existing(db)
        assert not dry['applied'] and not dry['errors'] and dry['changed'] == 2
        assert all(p.name_en == 'Old Enoxaparin label' for p in db.scalars(select(Product)))
        applied = identity.enrich_existing(db, apply=True)
        assert applied['applied'] and not applied['errors'] and applied['changed'] == 2
        for product_id, pack_id in reviewed:
            product, pack = db.get(Product, product_id), db.get(Packaging, pack_id)
            assert (product.slug, product.brand_id, product.cas, product.availability, product.supplier_stock,
                    product.storage, product.texts) == before[product_id][:-1]
            assert product.version == before[product_id][-1] + 1
            assert product.catalog_number == '1235831' and product.name_en == identity.NAME
            assert product.seo['ru']['description'] == 'Existing metadata'
            assert pack.key == '1-ampoule' and pack.unit == 'ampoule' and pack.label_en == '1 ampoule'
            assert pack.availability == 'in_stock' and pack.price_estimate == Decimal('543.21')
            assert pack.crm_packing_id == 'existing-crm-pack'
        assert list(db.scalars(select(Document.href))) == ['/existing-sds.pdf', '/existing-sds.pdf']
        assert payload(db, request)[0] == old_body
        assert db.scalar(select(func.count()).select_from(AuditEntry)) == 2
        again = identity.enrich_existing(db, apply=True)
        assert again['applied'] and again['changed'] == 0
        assert db.scalar(select(func.count()).select_from(AuditEntry)) == 2
        assert all(p.version == before[p.id][-1] + 1 for p in db.scalars(select(Product)))


@pytest.mark.parametrize('conflict', ['sku', 'packaging'])
def test_conflicts_refuse_both_records_without_partial_changes(sessions, reviewed, conflict):
    with sessions.begin() as db:
        channel = db.get(Product, reviewed[1][0])
        if conflict == 'sku':
            db.add(Product(brand_id=channel.brand_id, slug='other-existing-sigma-record', catalog_number='1235831',
                           catalog_number_norm='1235831', name_en='Another product'))
        else:
            db.add(Packaging(product_id=channel.id, key='another-amp', amount=Decimal(1), unit='ampoule',
                             label_ru='1 амп.', label_en='1 ampoule', catalog_number='1235831-1AMP',
                             catalog_number_norm=compact('1235831-1AMP')))
        db.flush()
        result = identity.enrich_existing(db, apply=True)
        assert result['errors'] and not result['applied']
        assert all(db.get(Product, pid).name_en == 'Old Enoxaparin label' for pid, _pack in reviewed)
        assert db.scalar(select(func.count()).select_from(AuditEntry)) == 0


def test_one_search_master_trusted_aliases_but_both_existing_pages_work(client, sessions, reviewed):
    fake = FakeEngine()
    with sessions.begin() as db:
        identity.enrich_existing(db, apply=True)
        unrelated = Product(brand_id=db.get(Product, reviewed[0][0]).brand_id, slug='unrelated',
                            catalog_number='other', catalog_number_norm='other', name_en='Unrelated',
                            status='published')
        db.add(unrelated)
        db.flush()
        assert indexer.index_pending(db, fake, product_ids=[pid for pid, _ in reviewed]) == 2
        assert unrelated.needs_index
        assert set(fake.documents) == {reviewed[0][0]}
        assert reviewed[1][0] in fake.deleted
        master = fake.documents[reviewed[0][0]]
        assert {'1235831', '12358311amp', 'usp1235831', 'usp12358311amp'} <= set(master['numbers'])
        assert master['cas'] is None
    for slug in (identity.MASTER_SLUG, identity.CHANNEL_SLUG):
        response = client.get(f'/api/v1/public/products/{slug}')
        assert response.status_code == 200, response.text
        product = response.json()['product']
        assert product['identity']['manufacturer'] == 'USP'
        assert product['identity']['canonicalSlug'] == identity.MASTER_SLUG
        assert product['packagings'][0]['label'] == '1 амп.'


class BatchEngine(FakeEngine):
    def __init__(self, exact, fuzzy=None):
        super().__init__()
        self.answers = [exact, fuzzy or []]

    def search(self, index, queries):
        answers = self.answers.pop(0)
        assert len(answers) == len(queries)
        return answers


def test_fuzzy_singleton_is_a_suggestion_and_exact_pack_is_not_first(sessions, reviewed):
    with sessions.begin() as db:
        identity.enrich_existing(db, apply=True)
        product = db.get(Product, reviewed[0][0])
        hit = documents.build(db, [product], documents.Context(db, True))[0][0]
    hit['packagings'].insert(0, {'key': '10-mg', 'label_ru': '10 мг', 'label_en': '10 mg',
                               'catalog_number': 'other-pack'})
    exact = query.batch(BatchEngine([Result([hit], 1)]), ['USP 1235831-1AMP 9'], 'ru')[0]
    assert exact['status'] == 'exact' and exact['quantity'] == 9 and exact['query'] == 'USP 1235831-1AMP'
    chosen = exact['candidates'][0]
    assert chosen['match'] == 'catalogNumber' and chosen['matchedPackagingId'] == f'{hit["id"]}-1-ampoule'
    assert chosen['matchedCatalogNumber'] == '1235831-1AMP'
    fuzzy = query.batch(BatchEngine([Result([], 0)], [Result([hit], 1)]), ['enoxaprin 9'], 'ru')[0]
    assert fuzzy['status'] == 'multiple' and fuzzy['candidates'][0]['matchedPackagingId'] is None
    assert fuzzy['candidates'][0]['match'] == 'name'
    # Even when the engine returns only one visible hit, a reported total >1 needs a human choice.
    ambiguous = query.batch(BatchEngine([Result([hit], 2)]), ['1235831'], 'ru')[0]
    assert ambiguous['status'] == 'multiple'


def test_nine_ampoules_reach_crm_without_quantity_or_identifier_loss(client, sessions, reviewed):
    with sessions.begin() as db:
        identity.enrich_existing(db, apply=True)
    item = {'siteProductId': reviewed[0][0], 'brand': 'USP', 'catalogNumber': '1235831-1AMP',
            'name': identity.NAME, 'packaging': '1 амп.', 'quantity': 9, 'unit': 'pack',
            'analogue': 'none', 'customPackaging': False}
    response = submit(client, form(items=[item]))
    assert response.status_code in (200, 201), response.text
    with sessions() as db:
        body, files = payload(db, db.scalar(select(SiteRequest)))
        assert not files
        row = body['items'][0]
        assert (row['site_product_id'], row['brand'], row['catalog_number'], row['quantity'], row['unit'],
                row['packaging'], row['analogue']) == (reviewed[0][0], 'USP', '1235831-1AMP', 9,
                                                        'pack', '1 амп.', 'none')


def test_quality_pilot_is_bounded_excludes_seed_and_respects_manual_noindex(sessions):
    with sessions.begin() as db:
        brand = Brand(slug='usp', name='USP')
        db.add(brand)
        db.flush()
        for i in range(35):
            product = Product(brand_id=brand.id, slug=f'pilot-{i}', catalog_number=f'P{i}',
                              catalog_number_norm=f'p{i}', name_en=f'Laboratory reference standard {i}',
                              status='published', source='seed' if i == 0 else 'import:assortment', cas='58-08-2',
                              index_override=False if i == 1 else None, popularity=100 - i)
            db.add(product)
            db.flush()
            db.add(Packaging(product_id=product.id, key='1-mg', label_ru='1 мг', label_en='1 mg'))
        db.flush()
        threshold = get_setting(db, 'index_threshold')
        report = pilot.quality_report(db, ['usp'], 20)
        assert report['selected'] == 20 and report['coverage'][0]['published'] == 34
        assert all(row['source'] != 'seed' for row in report['candidates'])
        assert report['candidates'][0]['action'] == 'explicit_noindex'
        assert not any(p.index_override is True for p in db.scalars(select(Product)))
        result = pilot.apply_quality_pilot(db, ['usp'], 20)
        assert result['opened'] == {'usp': 19}
        assert db.scalar(select(Product.index_override).where(Product.slug == 'pilot-1')) is False
        assert get_setting(db, 'index_threshold') == threshold
        assert db.scalar(select(func.count()).select_from(Product).where(Product.indexable.is_(True))) == 19
        with pytest.raises(ValueError):
            pilot.quality_report(db, ['usp'], 51)


def test_enrichment_cli_revalidates_both_product_tags_after_targeted_index(sessions, reviewed, monkeypatch, capsys):
    monkeypatch.setattr(cli, 'SessionLocal', sessions)
    indexed, invalidated = [], []

    def index(ids):
        indexed.append(ids)
        return len(ids)

    def revalidate(tags):
        invalidated.append(tags)
        return True

    monkeypatch.setattr(cli, '_index_targeted', index)
    monkeypatch.setattr(storefront, 'revalidate', revalidate)
    cli._enrich_usp(argparse.Namespace(apply=True))
    result = json.loads(capsys.readouterr().out)
    assert result['indexed'] == 2 and result['cacheInvalidated'] is True
    assert indexed == [[product_id for product_id, _pack in reviewed]]
    assert invalidated == [['catalog', f'product:{identity.MASTER_SLUG}', f'product:{identity.CHANNEL_SLUG}']]
    # A preview never touches the engine or the storefront cache.
    cli._enrich_usp(argparse.Namespace(apply=False))
    assert json.loads(capsys.readouterr().out)['applied'] is False
    assert len(indexed) == len(invalidated) == 1


def test_exact_production_placeholders_keep_ids_but_public_and_search_show_one_ampoule(
        client, sessions, production_placeholders):
    ids = production_placeholders
    fake = FakeEngine()
    old = form(items=[{'siteProductId': ids['master'], 'brand': 'USP', 'catalogNumber': '1235831',
                      'name': 'Original customer label', 'packaging': '1 шт.', 'quantity': 9, 'unit': 'pack'}])
    assert submit(client, old).status_code == 201
    with sessions.begin() as db:
        request = db.scalar(select(SiteRequest))
        historical = deepcopy(payload(db, request)[0])
        dry = identity.enrich_existing(db)
        assert not dry['errors'] and dry['changed'] == 2 and not dry['applied']
        assert dry['products'][0]['packagingId'] == ids['vial']
        new_id = dry['products'][1]['packagingId']
        assert identity.enrich_existing(db)['products'][1]['packagingId'] == new_id
        assert db.scalar(select(func.count()).select_from(Packaging)) == 2
        assert identity.enrich_existing(db, apply=True)['applied']
        master = db.get(Product, ids['master'])
        reviewed_identity = deepcopy(master.seo['identity'])
        assert reviewed_identity['verifiedPackagingId'] == ids['vial']
        assert reviewed_identity['legacyPackagingIds'] == [ids['pcs']]
        old_pcs, corrected = db.get(Packaging, ids['pcs']), db.get(Packaging, ids['vial'])
        assert (old_pcs.key, old_pcs.label_ru, old_pcs.unit, old_pcs.catalog_number) == ('1-pcs', '1 шт.', 'pcs', None)
        assert (corrected.key, corrected.unit, corrected.catalog_number) == ('1-ampoule', 'ampoule', '1235831-1AMP')
        assert corrected.availability == 'in_stock' and corrected.price_estimate == Decimal('543.21')
        assert corrected.crm_packing_id == 'old-pack-link'
        assert db.get(Packaging, new_id).product_id == ids['channel']
        assert db.scalar(select(func.count()).select_from(Packaging)) == 3
        assert payload(db, request)[0] == historical
        assert identity.enrich_existing(db, apply=True)['changed'] == 0
        assert master.seo['identity'] == reviewed_identity
        indexer.index_pending(db, fake, product_ids=[ids['master'], ids['channel']])
        assert set(fake.documents) == {ids['master']}
        assert fake.documents[ids['master']]['packs'] == ['1-ampoule']
        assert len(fake.documents[ids['master']]['packagings']) == 1
    for slug in (identity.MASTER_SLUG, identity.CHANNEL_SLUG):
        response = client.get(f'/api/v1/public/products/{slug}')
        assert response.status_code == 200, response.text
        packs = response.json()['product']['packagings']
        assert [(pack['label'], pack['catalogNumber']) for pack in packs] == [('1 амп.', '1235831-1AMP')]


@pytest.mark.parametrize('change', ['other_id', 'extra_pack', 'numbered_placeholder'])
def test_production_exception_does_not_resolve_other_ambiguities(sessions, production_placeholders, change):
    ids = production_placeholders
    with sessions.begin() as db:
        master = db.get(Product, ids['master'])
        if change == 'other_id':
            # Keep the same names/keys on another product: the reviewed exception is tied to the real ID.
            master.slug = 'old-master-before-test'
            copy = Product(brand_id=master.brand_id, slug=identity.MASTER_SLUG, catalog_number='temporary',
                           catalog_number_norm='temporary', name_en=master.name_en)
            master.catalog_number_norm = 'old-record'
            db.add(copy)
            db.flush()
            copy.catalog_number = '1235831'
            copy.catalog_number_norm = '1235831'
            for pack in db.scalars(select(Packaging).where(Packaging.product_id == master.id)):
                pack.product_id = copy.id
        elif change == 'extra_pack':
            db.add(Packaging(product_id=master.id, key='another-placeholder', label_ru='Другая', label_en='Other'))
        else:
            db.get(Packaging, ids['pcs']).catalog_number = 'another-number'
        db.flush()
        result = identity.enrich_existing(db, apply=True)
        assert result['errors'] and not result['applied']
        assert db.scalar(select(func.count()).select_from(AuditEntry)) == 0


def test_import_preserves_reviewed_pack_and_does_not_publish_new_unreviewed_variants(
        client, sessions, production_placeholders, tmp_path):
    ids = production_placeholders
    with sessions.begin() as db:
        assert identity.enrich_existing(db, apply=True)['applied']
    path = assortment(tmp_path / 'reload.xlsx', [
        ('Wrong new import name', '1235831-1AMP', None, 'USP', '1 ampoule'),
        ('Wrong new import name', '1235831', None, 'USP', '1viala'),
        ('Wrong new import name', '1235831-1AMP', None, 'Sigma-Aldrich', '1 ampoule'),
    ])
    imported = run.import_files(sessions, [path], source='assortment')
    assert imported['files'][0].get('created', 0) == 0
    with sessions.begin() as db:
        master = db.get(Product, ids['master'])
        assert db.scalar(select(func.count()).select_from(Product)) == 2
        assert master.name_en == identity.NAME and master.catalog_number == '1235831'
        verified = db.get(Packaging, ids['vial'])
        assert (verified.key, verified.label_ru, verified.catalog_number) == ('1-ampoule', '1 амп.', '1235831-1AMP')
        assert '1viala' in set(db.scalars(select(Packaging.key).where(Packaging.product_id == master.id)))
        # Simulate another future source/CRM adding a variant; it stays stored but cannot bypass the allowlist.
        db.add(Packaging(product_id=master.id, key='future-unreviewed', label_ru='Не проверено', label_en='Unreviewed'))
        db.flush()
        fake = FakeEngine()
        indexer.index_pending(db, fake, product_ids=[ids['master'], ids['channel']])
        assert fake.documents[ids['master']]['packs'] == ['1-ampoule']
    response = client.get(f'/api/v1/public/products/{identity.MASTER_SLUG}')
    assert [pack['label'] for pack in response.json()['product']['packagings']] == ['1 амп.']
