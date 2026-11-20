"""Upgrade legacy stock observations without losing source evidence or historic request identities."""

import importlib.util
from datetime import timedelta
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.catalog.models import Brand, CatalogSetting, CompetitorOffer, Packaging, Product
from app.catalog.settings import DEFAULTS, get_setting, set_setting
from app.core.db import as_utc, utcnow
from app.requests.models import SiteRequestItem
from tests.support import form, submit


def migrate_legacy(engine):
    path = Path(__file__).resolve().parents[2] / 'alembic' / 'versions' / '0013_stock_catalog.py'
    spec = importlib.util.spec_from_file_location('stock_migration_0013', path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            # Recreate revision 0012's four affected table shapes while retaining realistic existing records.
            migration.downgrade()
            assert 'supplier_stock_until' not in {column['name'] for column in sa.inspect(connection).get_columns('products')}
            migration.upgrade()


def test_upgrade_resets_unsafe_links_and_restarts_all_sources_but_preserves_observations(engine, sessions, client):
    accepted = submit(client, form())
    assert accepted.status_code == 201, accepted.text
    now = utcnow()
    observed = now - timedelta(days=2)
    with sessions.begin() as db:
        brand = Brand(slug='legacy', name='Legacy manufacturer')
        db.add(brand)
        db.flush()
        supplier = Product(brand_id=brand.id, catalog_number='SOURCE-SKU', catalog_number_norm='sourcesku',
                           slug='supplier-product', name_en='Supplier product', availability='on_order',
                           supplier_stock=True, supplier_stock_until=now + timedelta(days=8), needs_index=False)
        own = Product(brand_id=brand.id, catalog_number='OWN-SKU', catalog_number_norm='ownsku',
                      slug='own-product', name_en='Own product', availability='in_stock', needs_index=False)
        db.add_all([supplier, own])
        db.flush()
        pack = Packaging(product_id=supplier.id, key='1-g', label_ru='1 г', label_en='1 g')
        db.add(pack)
        db.flush()
        linked = CompetitorOffer(source='chimmed', external_id='legacy-linked', brand_name=brand.name,
                                 catalog_number='SOURCE-SKU', catalog_number_norm='sourcesku',
                                 name='Supplier original title', cas='50-00-0', pack='1 g', quantity=7,
                                 price='PRIVATE ORIGINAL PRICE', url='https://chimmed-new.ru/products/item',
                                 product_id=supplier.id, packaging_id=pack.id, first_seen_at=observed,
                                 seen_at=observed)
        orphan = CompetitorOffer(source='skygen', external_id='legacy-orphan', brand_name='Original brand',
                                 catalog_number='ORPHAN-SKU', catalog_number_norm='orphansku', name='Original title',
                                 url='https://klad.skygen.com/catalog/item/', product_id=None,
                                 packaging_id='removed-product-pack', first_seen_at=observed, seen_at=observed)
        db.add_all([linked, orphan])
        set_setting(db, 'competitor_stock', {'sources': ['skygen', 'chimmed', 'skygen'],
                    'every_days': 5, 'keep_days': 7, 'pause_seconds': 3.5,
                    'brand_aliases': {'Reviewed supplier name': 'legacy'}})
        set_setting(db, 'competitor_run', {'startedAt': observed.isoformat(),
                    'queue': [{'s': 'chimmed', 'k': 'list', 'm': 'Legacy'}]})
        set_setting(db, 'competitor_results', {'finishedAt': observed.isoformat(), 'left': 4,
                    'sources': {'chimmed': {'offers': 11, 'complete': True}}})
        request_item = db.scalar(sa.select(SiteRequestItem).where(
            SiteRequestItem.request_id == accepted.json()['siteRequestId']))
        assert request_item is not None
        request_identity = (request_item.id, request_item.request_id, request_item.catalog_number,
                            request_item.name, request_item.packaging, request_item.quantity)
        ids = supplier.id, own.id, linked.id, orphan.id
    migrate_legacy(engine)
    with sessions() as db:
        supplier, own = [db.get(Product, identifier) for identifier in ids[:2]]
        assert supplier is not None and own is not None
        assert not supplier.supplier_stock and supplier.supplier_stock_until is None and supplier.needs_index
        assert supplier.availability == 'on_order'
        assert own.availability == 'in_stock' and not own.needs_index
        rows = list(db.scalars(sa.select(CompetitorOffer).order_by(CompetitorOffer.external_id)))
        assert {row.id for row in rows} == set(ids[2:])
        assert all(row.product_id is None and row.packaging_id is None and row.stock_updated_at is None for row in rows)
        linked = next(row for row in rows if row.external_id == 'legacy-linked')
        assert (linked.source, linked.brand_name, linked.catalog_number, linked.name, linked.cas, linked.pack,
                linked.quantity, linked.price, linked.url) == (
                    'chimmed', 'Legacy manufacturer', 'SOURCE-SKU', 'Supplier original title', '50-00-0', '1 g',
                    7, 'PRIVATE ORIGINAL PRICE', 'https://chimmed-new.ru/products/item')
        assert as_utc(linked.first_seen_at) == as_utc(linked.seen_at) == observed
        stock = get_setting(db, 'competitor_stock')
        assert stock['sources'][:2] == ['skygen', 'chimmed']
        assert len(stock['sources']) == 11 and set(stock['sources']) == set(DEFAULTS['competitor_stock']['sources'])
        assert {key: stock[key] for key in ('every_days', 'keep_days', 'pause_seconds', 'brand_aliases')} == {
            'every_days': 5, 'keep_days': 7, 'pause_seconds': 3.5,
            'brand_aliases': {'Reviewed supplier name': 'legacy'}}
        assert get_setting(db, 'competitor_run') is None
        assert get_setting(db, 'competitor_results') == {
            'finishedAt': None, 'left': 4, 'sources': {'chimmed': {'offers': 11, 'complete': True}}}
        request_item = db.get(SiteRequestItem, request_identity[0])
        assert request_item is not None
        assert (request_item.id, request_item.request_id, request_item.catalog_number, request_item.name,
                request_item.packaging, request_item.quantity) == request_identity
        assert request_item.site_packaging_id is None and request_item.stock_snapshot is None


def test_upgrade_without_stored_settings_keeps_all_sources_available_from_defaults(engine, sessions):
    migrate_legacy(engine)
    with sessions() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(CatalogSetting)) == 0
        assert len(get_setting(db, 'competitor_stock')['sources']) == 11
        assert get_setting(db, 'competitor_run') is None
