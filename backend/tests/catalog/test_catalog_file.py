"""The business's catalog by category (31.10.2026): every sheet after the contents, the column titles under a title
row, the card's category from the file's direction, category and subgroup, and the directions not sold skipped."""

from sqlalchemy import select

from app.catalog.importer import run
from app.catalog.importer.reader import tables
from app.catalog.importer.rules import SKIP, file_category
from app.catalog.models import Category, ImportIssue, Product, ProductCategory
from tests.catalog.support import CATALOG_HEADER, assortment, catalog_file

CHEM, STD, CHROM = 'Химические реактивы', 'Стандарты и эталонные материалы', 'Хроматография'
Row = tuple[str, str, str, str, str, str | None, str, str | None]
SHEETS: dict[str, list[Row]] = {
    'Химия 1': [
        (CHEM, 'Органические соединения и строительные блоки', 'Гетероциклические соединения', '4-Benzylmorpholine',
         'CS-BB-2041', '10316-00-4', 'Clearsynth', '1 г'),
        (CHEM, 'Растворители', '', 'Water, ultra pure for HPLC', 'W-100-1L', None, 'Sigma-Aldrich', '1 л'),
        # USP sells only reference standards: its own subcategory whatever the file's words say.
        (CHEM, 'Органические соединения и строительные блоки', '', 'Carbamazepine', '1100000', '298-46-4', 'USP',
         '200 мг'),
        (CHEM, 'Неорганические соединения, кислоты и соли', '', 'Sodium chloride', '', None, 'Sigma-Aldrich', None),
    ],
    'Стандарты': [
        (STD, 'Изотопно-меченые соединения', '', 'Caffeine-d9', 'CS-D-9', None, 'Clearsynth', '5 мг'),
        (STD, 'Аналитические стандарты и CRM', '', 'Caffeine, Pharmaceutical Secondary Standard; Certified Reference '
         'Material', 'PHR0183X', '58-08-2', 'Merck', None),
    ],
    'Хроматография': [
        (CHROM, 'Колонки хроматографические', 'Колонки для ГХ', 'DB-5ms GC Column, 30 m, 0.25 mm', '122-5532',
         None, 'Agilent Technologies', '1 шт'),
        (CHROM, 'Колонки хроматографические', 'Колонки для ВЭЖХ/УВЭЖХ', 'XBridge C18 Column, 5 µm, 4.6 x 150 mm',
         '186003116', None, 'Waters', None),
    ],
    'Антитела 1': [
        ('Антитела и иммуноанализ', 'Антитела первичные (немеченые)', '', '(PSER392)-P53', 'P3116', None,
         'Sigma-Aldrich', None),
    ],
    'Клет. биология': [
        ('Клеточная биология и микробиология', 'Микробиология: питательные среды и добавки', '', 'Nutrient Agar',
         'M001-500G', None, 'HiMedia Laboratories', '500 г'),
        ('Клеточная биология и микробиология', 'Штаммы, клеточные линии и контрольные культуры', '',
         'Escherichia coli strain', 'KWIK-0335', None, 'Sigma-Aldrich', None),
    ],
    'Посуда и расходники': [
        ('Лабораторная посуда и расходные материалы', 'Фильтры, мембраны и фильтровальная бумага', '',
         'Syringe filter PTFE 0.45 µm, 25 mm', 'SF-PTFE-45', None, 'Macherey-Nagel', '100 шт'),
        ('Лабораторная посуда и расходные материалы', 'Лабораторная посуда, пластик и принадлежности', '',
         'Beaker 250 ml', 'BK-250', None, 'Duran', '1 шт'),
    ],
    'Оборудование': [
        ('Лабораторное оборудование и мебель', 'Приборы и оборудование', '', 'Magnetic stirrer', 'MS-1', None,
         'IKA', '1 шт'),
    ],
    'Прочее': [
        ('Прочие товары', 'Без явной категории (требуют уточнения)', '', 'Lab cart', 'CART-1', None,
         'Sigma-Aldrich', None),
    ],
}


def placed(db) -> dict[str, str]:
    return dict(db.execute(select(Product.catalog_number, Category.path)
                           .join(ProductCategory, ProductCategory.product_id == Product.id)
                           .join(Category, Category.id == ProductCategory.category_id)
                           .where(ProductCategory.is_primary.is_(True))).all())


def test_tables_skip_contents_and_find_the_header_under_a_title(tmp_path):
    path = catalog_file(tmp_path / 'catalog.xlsx', SHEETS)
    wanted = [['Производитель', 'Кат. №']]
    found = list(tables(path, wanted=wanted, all_sheets=True))
    assert [t.sheet for t in found] == list(SHEETS)
    first = found[0]
    assert first.header == CATALOG_HEADER and first.header_row == 2
    assert next(first.rows)[4] == '4-Benzylmorpholine'
    # Without «all sheets» only the first sheet with a header is read, not the contents.
    only = list(tables(path, wanted=wanted))
    assert [t.sheet for t in only] == ['Химия 1']
    # A file whose columns are not there is read as it is, so the import names the missing ones.
    plain = list(tables(assortment(tmp_path / 'a.xlsx', [('X', '1', None, 'Waters', None)]), wanted=[['Бренд']]))
    assert len(plain) == 1 and plain[0].header[0] == '№' and plain[0].header_row == 1


def test_file_categories_map_directions_and_keep_publishers():
    assert file_category(CHEM, 'Растворители', '', 'Sigma-Aldrich', 'Water') == 'reagents/solvents'
    assert file_category(' химические  реактивы ', 'растворители', '', 'Merck', 'Water') == 'reagents/solvents'
    assert file_category(CHEM, 'Неизвестная категория', '', 'ABCR', 'X') == 'reagents'
    assert file_category(STD, 'Аналитические стандарты и CRM', '', 'EDQM', 'Paracetamol CRS') == \
        'reference-standards/edqm'
    assert file_category('Антитела и иммуноанализ', 'Вторичные антитела', '', 'USP', 'X') == 'reference-standards/usp'
    assert file_category('Лабораторное оборудование и мебель', '', '', 'USP', 'X') == SKIP
    assert file_category('Новое направление', '', '', 'Waters', 'XBridge C18 Column') is None


def test_the_catalog_file_lays_products_into_the_site_categories(seeded, tmp_path):
    path = catalog_file(tmp_path / 'Каталог_продукции_по_категориям.xlsx', SHEETS)
    result = run.import_files(seeded, [path], source='catalog')
    counters = result['files'][0]
    assert counters['sheets'] == len(SHEETS)
    # Glassware except filters, equipment and «Прочие товары» are not sold.
    assert counters['skipped_not_sold'] == 3
    with seeded() as db:
        where = placed(db)
        assert where['CS-BB-2041'] == 'reagents/organic'
        assert where['W-100'] == 'reagents/solvents'  # «-1L» is its packaging
        assert where['1100000'] == 'reference-standards/usp'
        assert where['CS-D-9'] == 'reference-standards/isotope-labelled'
        assert where['PHR0183X'] == 'reference-standards/merck'
        assert where['122-5532'] == 'chromatography/gc-columns'
        assert where['P3116'] == 'biochemistry/antibodies'
        assert where['M001'] == 'biochemistry/cell-biology'
        assert where['KWIK-0335'] == 'biological-standards'
        assert where['SF-PTFE-45'] == 'chromatography/filters'
        numbers = set(db.scalars(select(Product.catalog_number)))
        assert not numbers & {'BK-250', 'MS-1', 'CART-1'}
        # The seed's card keeps its own category and name; the file adds what it lacks.
        column = db.scalar(select(Product).where(Product.catalog_number == '186003116'))
        assert column.source == 'seed' and where['186003116'] == 'chromatography/hplc-columns'
        # The journal says on which sheet and row an issue is.
        empty = db.scalar(select(ImportIssue).where(ImportIssue.code == 'CATALOG_NUMBER_EMPTY'))
        assert (empty.values['sheet'], empty.row_number) == ('Химия 1', 6)
        # The source's descriptions and characteristics' text are never stored.
        assert all('Текст описания' not in str(v) for v in db.scalars(select(ImportIssue.values)))
    summary = '\n'.join(run.issue_summary(seeded(), result['files'][0]['batch']))
    assert 'лист «Химия 1», строка 6' in summary


def test_recategorize_keeps_the_categories_the_file_gave(seeded, tmp_path):
    run.import_files(seeded, [catalog_file(tmp_path / 'catalog.xlsx', SHEETS)], source='catalog')
    run.recategorize(seeded, only_missing=False)
    with seeded() as db:
        where = placed(db)
        # By the brand rules alone a Sigma-Aldrich antibody would be a reagent.
        assert where['P3116'] == 'biochemistry/antibodies'
        assert where['CS-BB-2041'] == 'reagents/organic'
