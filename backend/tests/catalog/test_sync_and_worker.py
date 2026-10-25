"""Flow F5 against a fake CRM, the worker's index queue and the lists of controlled substances."""

import hashlib
import hmac
import json
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select

from app.catalog import brands_sync, controlled, seed
from app.catalog.importer import run
from app.catalog.models import Brand, BrandAlias, Product, SlugRedirect
from app.catalog.search import indexer
from app.catalog.settings import get_setting
from app.core.config import settings
from app.outbox import worker
from app.outbox.models import OutboxEvent
from tests.catalog.support import FakeEngine


def crm(entries: list[dict], seen: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        stamp = request.headers['x-site-timestamp']
        target = request.url.raw_path.decode()
        expected = hmac.new(settings.crm_signing_secret.encode(), f'{stamp}.GET {target}'.encode(), hashlib.sha256)
        if request.headers['x-site-signature'] != f'sha256={expected.hexdigest()}':
            return httpx.Response(401, json={'code': 'INTEGRATION_SIGNATURE_INVALID'})
        cursor = request.url.params.get('cursor')
        page = entries[1:] if cursor else entries[:1]
        return httpx.Response(200, json={'items': page, 'next_cursor': None if cursor or len(entries) == 1 else 'c1'})
    return httpx.MockTransport(handler)


def entry(id_: str, name: str, aliases: list[str], merged: str | None = None, at: str = '2026-10-24T10:00:00+00:00'):
    return {'id': id_, 'name': name, 'internal_code': 1, 'aliases': aliases, 'umbrella_id': None,
            'merged_into_id': merged, 'updated_at': at}


def test_registry_links_creates_and_merges_brands(seeded):
    seen: list[httpx.Request] = []
    entries = [entry('m-waters', 'Waters', ['Waters', 'Waters Corporation', 'Waters Technologies']),
               entry('m-new', 'Shodex', ['Shodex', 'Showa Denko'], at='2026-10-24T11:00:00+00:00'),
               entry('m-lgc', 'LGC', ['LGC Standards'], at='2026-10-24T12:00:00+00:00'),
               entry('m-old', 'Dr. Ehrenstorfer', ['Dr. Ehrenstorfer'], merged='m-lgc', at='2026-10-24T13:00:00+00:00')]
    with seeded.begin() as db:
        old = Brand(slug='dr-ehrenstorfer', name='Dr. Ehrenstorfer', page_published=True, content={})
        db.add(old)
        db.flush()
        lgc = db.scalar(select(Brand).where(Brand.slug == 'lgc'))
        sample = db.scalar(select(Product).where(Product.brand_id == lgc.id))
        db.add(Product(brand_id=old.id, catalog_number='DRE-1', catalog_number_norm='dre1', slug='dre-1', name_en='x',
                       status='published'))
        db.add(Product(brand_id=old.id, catalog_number=sample.catalog_number,
                       catalog_number_norm=sample.catalog_number_norm, slug='dre-dup', name_en='dup', status='published'))
    counters = brands_sync.sync(seeded, transport=crm(entries, seen))
    assert counters['entries'] == 4 and counters['created'] == 1 and counters['linked'] >= 2
    assert len(seen) == 2 and seen[0].headers['authorization'] == f'Bearer {settings.crm_token}'
    with seeded() as db:
        waters = db.scalar(select(Brand).where(Brand.slug == 'waters'))
        assert waters.crm_manufacturer_id == 'm-waters'
        assert db.scalar(select(BrandAlias.brand_id).where(BrandAlias.name == 'Waters Technologies')) == waters.id
        shodex = db.scalar(select(Brand).where(Brand.crm_manufacturer_id == 'm-new'))
        assert shodex is not None and not shodex.page_published
        old = db.scalar(select(Brand).where(Brand.slug == 'dr-ehrenstorfer'))
        lgc = db.scalar(select(Brand).where(Brand.slug == 'lgc'))
        assert old.merged_into_id == lgc.id and counters['moved_products'] == 1
        assert db.scalar(select(Product.brand_id).where(Product.slug == 'dre-1')) == lgc.id
        # The same number already at the main brand stays where it was.
        assert db.scalar(select(Product.brand_id).where(Product.slug == 'dre-dup')) == old.id
        assert db.scalar(select(SlugRedirect.target_id).where(SlugRedirect.old_slug == 'dr-ehrenstorfer')) == lgc.id
        assert get_setting(db, 'brands_synced_at') == '2026-10-24T13:00:00+00:00'
        assert not brands_sync.due(db, datetime.now(UTC))


def test_sync_is_skipped_without_crm_settings(seeded, monkeypatch):
    monkeypatch.setattr(settings, 'crm_token', '')
    assert 'skipped' in brands_sync.sync(seeded)


def test_worker_pushes_the_queue_and_drops_storefront_cache(seeded, monkeypatch):
    engine = FakeEngine()
    calls: list[dict] = []
    monkeypatch.setattr(worker, 'search_engine', lambda: engine)
    monkeypatch.setattr(worker, 'SessionLocal', seeded)
    monkeypatch.setattr(settings, 'web_url', 'http://web:3000')
    monkeypatch.setattr(settings, 'revalidate_secret', 'secret')

    def post(url: str, **kwargs: object) -> httpx.Response:
        calls.append({'url': url, **kwargs})
        return httpx.Response(200)

    monkeypatch.setattr(worker.httpx, 'post', post)
    assert worker.index_catalog(limit=10) > 400
    with seeded() as db:
        total = db.scalar(select(func.count()).select_from(Product))
        hidden = db.scalar(select(func.count()).select_from(Product).where(Product.controlled.is_not(None)))
        assert db.scalar(select(func.count()).select_from(Product).where(Product.needs_index.is_(True))) == 0
    assert len(engine.documents) == total - hidden and len(engine.deleted) == hidden
    assert calls and calls[0]['url'] == 'http://web:3000/api/revalidate/'
    assert 'product:edqm-y0001897-oxcarbazepine-crs' in calls[0]['json']['tags']
    assert calls[0]['headers'] == {'X-Revalidate-Secret': 'secret'}
    document = engine.documents[next(d for d, v in engine.documents.items() if v['catalog_number'] == 'Y0001897')]
    assert document['numbers'] == ['y0001897'] and document['cas_numbers'] == ['28721075']
    assert 'reference-standards' in document['categories'] and document['category_top'] == 'reference-standards'


def test_rolled_back_products_leave_the_index(seeded, tmp_path, monkeypatch):
    from tests.catalog.support import assortment

    engine = FakeEngine()
    monkeypatch.setattr(worker, 'search_engine', lambda: engine)
    monkeypatch.setattr(worker, 'SessionLocal', seeded)
    path = assortment(tmp_path / 'a.xlsx', [('Thing', 'T-1', None, 'Waters', None)])
    result = run.import_files(seeded, [path], source='assortment')
    with seeded.begin() as db:
        indexer.index_pending(db, engine, limit=5000)
        new_id = db.scalar(select(Product.id).where(Product.catalog_number == 'T-1'))
        run.rollback(db, result['files'][0]['batch'])
    assert new_id in engine.documents
    worker.run_once(housekeeping=False)
    assert new_id not in engine.documents
    with seeded() as db:
        assert db.scalar(select(OutboxEvent.status).where(OutboxEvent.kind == 'search.delete')) == 'succeeded'


def test_controlled_register_marks_and_respects_the_chemist(seeded, tmp_path):
    path = tmp_path / 'register.xlsx'
    run.write_xlsx(path, [['Перечень', 'Название', 'CAS', 'Синонимы'],
                          ['ПП 681', 'Кофеин', '58-08-2', 'caffeine'],
                          ['ПП 964', 'Трамадол', '27203-92-5; 36282-47-0', 'tramadol']])
    entries = controlled.read_register_xlsx(path)
    assert [e['list'] for e in entries] == ['pp681', 'pp964']
    with seeded.begin() as db:
        cleared = db.scalar(select(Product).where(Product.catalog_number == 'PHR0183'))  # Merck caffeine standard
        cleared.controlled_state = 'cleared'
        controlled.load_register(db, entries)
        changed = run.recheck_controlled(db)
    assert changed > 0
    with seeded() as db:
        caffeine = db.scalars(select(Product).where(Product.cas == '58-08-2')).all()
        states = {p.catalog_number: (p.controlled, p.controlled_state) for p in caffeine}
        assert states['PHR0183'] == (None, 'cleared')
        assert any(value == ('pp681', 'auto') for value in states.values())
        # Morphine left the register: the product is visible again.
        assert db.scalar(select(func.count()).select_from(Product).where(Product.controlled == 'pp681',
                                                                          Product.cas == '57-27-2')) == 0


def test_seed_is_idempotent(seeded):
    with seeded() as db:
        before = db.scalar(select(func.count()).select_from(Product))
    with seeded.begin() as db:
        seed.load(db)
    with seeded() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == before
        assert json.loads(json.dumps(get_setting(db, 'home_products')))[0] == 'edqm-y0001897-oxcarbazepine-crs'
