"""Import of price lists (TZ 9.5, 9.6): rows to products, packagings, brands, conflicts, journal and rollback."""

from sqlalchemy import func, select

from app.catalog import seed
from app.catalog.importer import run
from app.catalog.importer.reader import read_rows
from app.catalog.models import (
    Brand,
    Category,
    ImportBatch,
    ImportIssue,
    Packaging,
    Product,
    ProductCategory,
)
from app.outbox.models import OutboxEvent
from tests.catalog.support import assortment

ROWS = [
    ('Oxcarbazepine CRS', 'CS-T-60514-5MG', '28721-07-5', 'Clearsynth', '5 мг'),
    ('Oxcarbazepine CRS', 'CS-T-60514-10MG', '28721-07-5', 'Clearsynth', '10 мг'),
    ('Окскарбазепин примесь A', 'CS-O-11', '28721-07-4', 'Clearsynth', None),
    ('0.007IN ID SS TUBING, 1/16IN OD, 20CM', '56715-U', None, 'Waters', '1 шт'),
    ('XBridge C18 Column, 130 Å, 5 µm, 4.6 mm X 150 mm', '186003116', None, 'Waters', None),
    ('γ-Моноклональные антитела', 'BML-GA1160-0025', None, 'Enzo Life Sciences', '25 мкл'),
    ('Химмед реактив', 'HM-1', None, 'Химмед', '1 кг'),
    ('', '', None, 'Waters', None),
]


def load(sessions, tmp_path, rows=ROWS, **kwargs):
    path = assortment(tmp_path / 'assortment.xlsx', rows)
    return run.import_files(sessions, [path], source=kwargs.pop('source', 'assortment'), **kwargs)


def test_reader_streams_the_export_shape(tmp_path):
    path = assortment(tmp_path / 'a.xlsx', ROWS[:1])
    rows = list(read_rows(path))
    assert rows[0][:5] == ['№', 'Наименование', 'Кат. №', 'CAS', 'Производитель']
    assert rows[1][1:6] == ['Oxcarbazepine CRS', 'CS-T-60514-5MG', '28721-07-5', 'Clearsynth', '5 мг']


def test_first_load_creates_products_packagings_and_brands(sessions, tmp_path):
    with sessions.begin() as db:
        seed.load(db)
    result = load(sessions, tmp_path)
    counters = result['files'][0]
    assert counters['skipped'] == 1  # the source's own brand is not imported
    assert counters['issues_error'] == 1  # an empty catalog number
    assert counters['issues_warning'] == 1  # an invalid CAS: the row is loaded without it
    with sessions() as db:
        clearsynth = db.scalars(select(Product).join(Brand).where(Brand.name == 'Clearsynth')
                                .order_by(Product.catalog_number)).all()
        # «-5MG» and «-10MG» are packagings of one product; the full numbers stay on the packagings.
        oxc = next(p for p in clearsynth if p.catalog_number == 'CS-T-60514')
        packs = db.scalars(select(Packaging).where(Packaging.product_id == oxc.id).order_by(Packaging.key)).all()
        assert [(p.key, p.catalog_number) for p in packs] == [('10-mg', 'CS-T-60514-10MG'), ('5-mg', 'CS-T-60514-5MG')]
        assert (oxc.availability, oxc.status, oxc.source) == ('on_order', 'published', 'import:assortment')
        # A translated name is the source's text: kept internally, the card is named by its number (NFR-09).
        impurity = next(p for p in clearsynth if p.catalog_number == 'CS-O-11')
        assert impurity.name_en == 'Clearsynth CS-O-11' and impurity.source_name == 'Окскарбазепин примесь A'
        assert impurity.cas is None and impurity.slug == 'clearsynth-cs-o-11'
        # Category by the rules: Clearsynth → impurity standards, a Waters column → HPLC columns.
        column = db.scalar(select(Product).where(Product.catalog_number == '186003116'))
        category_of = dict(db.execute(
            select(Product.catalog_number, Category.path)
            .join(ProductCategory, ProductCategory.product_id == Product.id)
            .join(Category, Category.id == ProductCategory.category_id).where(ProductCategory.is_primary.is_(True))).all())
        assert category_of['CS-T-60514'] == 'reference-standards/impurity-standards'
        assert category_of['186003116'] == 'chromatography/hplc-columns' and column.card_type == 'equipment'
        assert category_of['56715-U'] == 'chromatography/fittings'
        assert category_of['BML-GA1160'] == 'biochemistry'  # an antibody of a biotech brand
        # A manufacturer met for the first time becomes a brand without a page, listed for review.
        enzo = db.scalar(select(Brand).where(Brand.name == 'Enzo Life Sciences'))
        assert enzo is not None and not enzo.page_published
        antibody = db.scalar(select(Product).where(Product.brand_id == enzo.id))
        assert antibody.source_name == 'γ-Моноклональные антитела'
        review = db.scalars(select(ImportIssue.code).where(ImportIssue.kind == 'review')).all()
        assert 'BRAND_CREATED' in review
        assert db.scalar(select(func.count()).select_from(Product).where(Product.needs_index.is_(True))) > 0


def test_reload_updates_without_duplicates_and_keeps_manual_fields(sessions, tmp_path):
    load(sessions, tmp_path)
    with sessions.begin() as db:
        product = db.scalar(select(Product).where(Product.catalog_number == '56715-U'))
        product.name_en = 'Stainless steel tubing 0.007 in'
        product.manual_fields = ['name_en']
    rows = [*ROWS, ('XBridge C18 Column, 130 Å, 5 µm, 4.6 mm X 150 mm', '186003116', None, 'Waters', '1 шт')]
    result = load(sessions, tmp_path, rows=rows)
    counters = result['files'][0]
    assert counters.get('created', 0) == 0
    with sessions() as db:
        assert db.scalar(select(Product.name_en).where(Product.catalog_number == '56715-U')) == \
            'Stainless steel tubing 0.007 in'
        column = db.scalar(select(Product).where(Product.catalog_number == '186003116'))
        assert db.scalar(select(func.count()).select_from(Packaging).where(Packaging.product_id == column.id)) == 1


def test_same_number_with_another_cas_is_a_conflict(sessions, tmp_path):
    load(sessions, tmp_path)
    result = load(sessions, tmp_path, rows=[('Oxcarbazepine CRS', 'CS-T-60514-5MG', '58-08-2', 'Clearsynth', '5 мг')])
    assert result['files'][0]['conflicts'] == 1
    with sessions() as db:
        assert db.scalar(select(Product.cas).where(Product.catalog_number == 'CS-T-60514')) == '28721-07-5'
        issue = db.scalar(select(ImportIssue).where(ImportIssue.code == 'CAS_CONFLICT'))
        assert issue.kind == 'conflict' and '58-08-2' in issue.message


def test_price_list_keeps_unknown_brands_waiting_and_reads_stock(sessions, tmp_path):
    with sessions.begin() as db:
        seed.load(db)
    header = ['Производитель', 'Кат. №', 'Наименование', 'CAS', 'Фасовка', 'Наличие']
    path = tmp_path / 'price.xlsx'
    run.write_xlsx(path, [header, ['EDQM', 'Y0001897', 'Oxcarbazepine CRS', '28721-07-5', '100 мг', 'В наличии'],
                          ['Unknown Maker', 'U-1', 'Thing', None, None, 'Под заказ'],
                          ['Unknown Maker', 'U-2', 'Thing 2', None, None, 'Под заказ']])
    result = run.import_files(sessions, [path], source='price')
    counters = result['files'][0]
    assert counters['unknown_brand_rows'] == 2 and counters['issues_error'] == 1
    with sessions() as db:
        product = db.scalar(select(Product).where(Product.catalog_number == 'Y0001897'))
        # The seed's own name stays; availability comes from the price list.
        assert product.name_en == 'Oxcarbazepine CRS' and product.availability == 'in_stock'
        assert db.scalar(select(func.count()).select_from(Brand).where(Brand.name == 'Unknown Maker')) == 0


def test_dry_run_changes_nothing(sessions, tmp_path):
    result = load(sessions, tmp_path, dry_run=True)
    assert result['files'][0]['created'] >= 5
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == 0
        assert db.scalar(select(ImportBatch.dry_run)) is True


def test_rollback_removes_created_and_restores_updated(sessions, tmp_path):
    with sessions.begin() as db:
        seed.load(db)
        before = db.scalar(select(func.count()).select_from(Product))
    first = load(sessions, tmp_path)
    header = ['Производитель', 'Кат. №', 'Наименование', 'CAS', 'Фасовка', 'Наличие']
    path = tmp_path / 'price.xlsx'
    run.write_xlsx(path, [header, ['EDQM', 'Y0001897', 'Oxcarbazepine CRS', '28721-07-5', '1 г', 'В наличии']])
    second = run.import_files(sessions, [path], source='price')
    with sessions.begin() as db:
        summary = run.rollback(db, second['files'][0]['batch'])
    assert summary['restored'] == 1 and summary['packagings_removed'] == 1
    with sessions.begin() as db:
        product = db.scalar(select(Product).where(Product.catalog_number == 'Y0001897'))
        assert product.availability == 'on_order'
        assert db.scalar(select(func.count()).select_from(Packaging).where(Packaging.product_id == product.id)) == 1
        summary = run.rollback(db, first['files'][0]['batch'])
        assert summary['deleted'] >= 4  # the seed already has the XBridge column
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == before
        assert db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.kind == 'search.delete')) == 1
        statuses = set(db.scalars(select(ImportBatch.status)))
        assert statuses == {'rolled_back'}


def test_issues_export_as_xlsx(sessions, tmp_path):
    result = load(sessions, tmp_path)
    out = tmp_path / 'issues.xlsx'
    with sessions() as db:
        count = run.export_issues(db, result['files'][0]['batch'], out)
    rows = list(read_rows(out))
    assert count == len(rows) - 1 and rows[0][:4] == ['Строка', 'Тип', 'Код', 'Сообщение']
    assert any(row[2] == 'CAS_INVALID' for row in rows[1:])
