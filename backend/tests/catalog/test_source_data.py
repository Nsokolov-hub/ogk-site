"""The source's own data never reaches the site: its links, ids, its brand and the text of its characteristics.

The site is indexed by its own catalog (TZ 9.6, NFR-09): from the assortment export only the list of items and
the manufacturer's facts are taken.
"""

import json

from sqlalchemy import func, select

from app.catalog import seed
from app.catalog.importer import run
from app.catalog.models import (
    Brand,
    BrandAlias,
    Category,
    ImportIssue,
    ImportSource,
    Packaging,
    Product,
    ProductCategory,
)
from app.catalog.search import documents, indexer
from tests.catalog.support import SOURCE_ID, SOURCE_LINK, FakeEngine, assortment

ROWS = [
    ('Oxcarbazepine', 'AB477228-1мг', '28721-07-5', 'ABCR', None),
    ('Окскарбазепин, ч.д.а.', 'AB477229', '28721-07-5', 'ABCR', '5 г'),
    ('CD27 / TNFRSF7 Antibody (APC), Mouse MAb', 'SIN-10039-MM09-A-25Tests', None, 'Sino Biological', '25 тест'),
    ('CD270 HUMAN, RECOMBINANT', 'SRP0562-100UG', None, 'Sigma-Aldrich', None),
    ('Химмед реактив', 'HM-1', None, 'Химмед', '1 кг'),
    ('Caffeine, Pharmaceutical Secondary Standard; Certified Reference Material', 'PHR0183X', '58-08-2', 'Merck', None),
]
CHARACTERISTICS = {
    1: 'Молекулярный вес: 252.27 g/mol; Формула: C15H12N2O2; Плотность: 1.2; Температура плавления: 215 °C',
    3: 'Альтернативное название: CD27; Хост: Мышь; Изотип: IgG1',
}


def everything_stored(db) -> str:
    """Every stored value of the catalog, the import journal and the sources, as one text."""
    parts = []
    for model in (Product, Packaging, Brand, BrandAlias, ImportIssue, ImportSource):
        for row in db.scalars(select(model)):
            parts.append(json.dumps({attr.key: getattr(row, attr.key) for attr in model.__mapper__.column_attrs},
                                    ensure_ascii=False, default=str))
    return '\n'.join(parts)


def test_links_ids_brand_and_characteristics_text_are_never_stored(seeded, tmp_path):
    path = assortment(tmp_path / 'export.xlsx', ROWS, CHARACTERISTICS)
    result = run.import_files(seeded, [path], source='assortment')
    assert result['files'][0]['skipped'] == 1
    with seeded() as db:
        stored = everything_stored(db)
        assert 'chimmed' not in stored.casefold() and SOURCE_LINK not in stored
        for i in range(1, len(ROWS) + 1):
            assert str(SOURCE_ID + i) not in stored
        assert 'химмед' not in stored.casefold()
        # From the characteristics only the formula and the weight; their other text is nowhere.
        assert 'Плотность' not in stored and 'Температура плавления' not in stored and 'Изотип' not in stored
        assert 'Текст описания источника' not in stored
        assert db.scalar(select(func.count()).select_from(Brand).where(func.lower(Brand.name).like('%химмед%'))) == 0


def test_public_api_and_index_show_none_of_the_source(seeded, tmp_path, client):
    path = assortment(tmp_path / 'export.xlsx', ROWS, CHARACTERISTICS)
    run.import_files(seeded, [path], source='assortment')
    engine = FakeEngine()
    with seeded.begin() as db:
        while indexer.index_pending(db, engine, limit=5000):
            pass
        slugs = list(db.scalars(select(Product.slug).where(Product.source == 'import:assortment')))
    index_text = json.dumps(list(engine.documents.values()), ensure_ascii=False)
    assert 'Окскарбазепин, ч.д.а.' not in index_text and 'chimmed' not in index_text.casefold()
    for slug in slugs:
        page = client.get(f'/api/v1/public/products/{slug}').text
        assert 'chimmed' not in page.casefold() and SOURCE_LINK not in page
        assert 'Окскарбазепин, ч.д.а.' not in page  # the source's translated name stays internal
    assert set(documents.INDEX_SETTINGS['searchableAttributes']).isdisjoint({'source_name'})


def test_facts_names_and_biochemistry(seeded, tmp_path):
    path = assortment(tmp_path / 'export.xlsx', ROWS, CHARACTERISTICS)
    run.import_files(seeded, [path], source='assortment')
    with seeded() as db:
        oxc = db.scalar(select(Product).where(Product.catalog_number == 'AB477228'))
        assert (oxc.formula, oxc.formula_hill, oxc.molecular_weight) == ('C15H12N2O2', 'C15H12N2O2', '252,27')
        assert oxc.name_en == 'Oxcarbazepine'  # a Latin name is the manufacturer's catalog name
        translated = db.scalar(select(Product).where(Product.catalog_number == 'AB477229'))
        assert translated.name_en == 'Oxcarbazepine'  # named by its substance (the seed knows the CAS)
        path_of = dict(db.execute(select(Product.catalog_number, Category.path)
                                  .join(ProductCategory, ProductCategory.product_id == Product.id)
                                  .join(Category, Category.id == ProductCategory.category_id)).all())
        assert path_of['SIN-10039-MM09-A'] == 'biochemistry'
        assert path_of['SRP0562'] == 'biochemistry'  # a reagent brand's recombinant protein
        assert path_of['PHR0183X'] == 'reference-standards/merck'
        assert path_of['AB477228'] == 'reagents'


def test_recategorize_places_products_left_without_a_category(seeded, tmp_path):
    path = assortment(tmp_path / 'export.xlsx', ROWS, CHARACTERISTICS)
    run.import_files(seeded, [path], source='assortment')
    with seeded.begin() as db:
        antibody = db.scalar(select(Product).where(Product.catalog_number == 'SIN-10039-MM09-A'))
        db.query(ProductCategory).filter(ProductCategory.product_id == antibody.id).delete()
        antibody.needs_index = False
        seed_product = db.scalar(select(Product).where(Product.catalog_number == 'Y0001897'))
        db.query(ProductCategory).filter(ProductCategory.product_id == seed_product.id).delete()
    counts = run.recategorize(seeded)
    assert counts['biochemistry'] == 1
    with seeded() as db:
        antibody = db.scalar(select(Product).where(Product.catalog_number == 'SIN-10039-MM09-A'))
        assert antibody.needs_index is True
        assert db.scalar(select(Category.path).join(ProductCategory).where(
            ProductCategory.product_id == antibody.id)) == 'biochemistry'
        # A product written by people (here the seed) keeps whatever a person decided.
        seed_product = db.scalar(select(Product).where(Product.catalog_number == 'Y0001897'))
        assert db.scalar(select(func.count()).select_from(ProductCategory).where(
            ProductCategory.product_id == seed_product.id)) == 0


def test_saved_template_learns_new_fields_without_losing_edits(sessions):
    with sessions.begin() as db:
        db.add(ImportSource(code='assortment', name='x', mapping={'brand': 'Бренд'}, options={'names': 'all'}))
    with sessions.begin() as db:
        source = run.ensure_source(db, 'assortment')
        assert source.mapping['brand'] == 'Бренд' and source.mapping['characteristics'] == 'Характеристики'
        assert source.options['names'] == 'all' and source.options['chemical_facts'] is True


def test_content_only_seed_has_structure_without_test_products(sessions):
    with sessions.begin() as db:
        counts = seed.load(db, products_too=False)
    assert counts['categories'] == 19 and 'products' not in counts
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == 0
        biochemistry = db.scalar(select(Category).where(Category.path == 'biochemistry'))
        assert biochemistry.name_en == 'Biochemistry and biotechnology' and biochemistry.content['ru']['h1']
