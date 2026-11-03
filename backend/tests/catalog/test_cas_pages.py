"""Substance pages by CAS number (/cas/<cas>/): names out of the brands' product names, which CAS numbers get a page,
the nightly build and the public API."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.catalog import cas_pages
from app.catalog.cas_pages import choose, display_name, stand_in
from app.catalog.models import Brand, CasPage, Category, Product, ProductCategory
from app.catalog.settings import set_setting

URL = '/api/v1/public'
ANILINE = '3535-88-4'


def test_a_product_name_gives_the_substance_without_grade_and_purity():
    assert display_name('Paracetamol CRS') == 'Paracetamol'
    assert display_name('Paracetamol, Pharmaceutical Secondary Standard; Certified Reference Material') == 'Paracetamol'
    assert display_name('4-Acetamidophenol; 98%') == '4-Acetamidophenol'
    assert display_name('ACETAMINOPHEN, MEETS USP TESTING SPEC&') == 'Acetaminophen'
    assert display_name('CAFFEINE BIOXTRA') == 'Caffeine'
    assert display_name('Metformin Hydrochloride Reference Standard') == 'Metformin Hydrochloride'
    # The salt stays: it is part of what is sold; commas inside a chemical name stay too.
    assert display_name('1,1-Dimethylbiguanide hydrochloride, 97%') == '1,1-Dimethylbiguanide hydrochloride'
    assert display_name('TRIUNDECANOIN (C11:0)') == 'Triundecanoin (C11:0)'
    assert display_name('5-tert-Butyl-2-methoxyaniline, 97%; .') == '5-tert-Butyl-2-methoxyaniline'
    # A part after a comma that changes the compound keeps the name whole.
    assert display_name('Benzaldehyde, 2,4-dibromo-') == 'Benzaldehyde, 2,4-dibromo-'
    assert display_name('Holmium(III) bromide, ultra dry, 99.98% (REO); .') == 'Holmium(III) bromide'
    assert display_name('TANSHINONE I >=98% (HPLC)') == 'Tanshinone I'
    assert display_name('SODIUM CHLORIDE SUITABLE FOR CELL CULTURE') == 'Sodium chloride'
    # A solution is another product than the substance: it does not name the page; nor does a registry code.
    assert display_name('4-ACETAMIDOPHENOL METHANOL SOLUTION') is None
    assert display_name('UNII-U2Y5OFN795') is None
    assert display_name('R320072 Water Ph-Q X,500LK') is None
    assert display_name('FR1574 Benzimidazol ,250GFL') is None
    assert display_name("ADENOSINE 2',3'-CYCLIC MONOPHOSPHATE&") is None


def test_stand_in_names_are_known():
    assert stand_in('Clearsynth CS-M-21728-1GMS', 'Clearsynth', 'csm217281gms')
    assert stand_in('Larodan 33-1100-9', 'Larodan', '3311009')
    assert not stand_in('Caffeine', 'Merck', '102584')


def test_the_name_most_brands_use_wins_and_the_others_are_synonyms():
    name, synonyms = choose([('Paracetamol', 'EDQM'), ('Paracetamol', 'USP'), ('Paracetamol', 'Merck'),
                             ('Acetaminophen', 'Sigma-Aldrich'), ('Acetaminophen', 'Sigma-Aldrich'),
                             ('4-Acetamidophenol', 'ABCR')])
    assert name == 'Paracetamol' and synonyms == ['Acetaminophen', '4-Acetamidophenol']
    # Mixed case is preferred to capitals within the same substance.
    assert choose([('CAFFEINE', 'Sigma-Aldrich'), ('Caffeine', 'Merck')]) == ('Caffeine', [])
    # A big page takes only the names two brands share as synonyms.
    noisy = [('Water', 'Merck'), ('Water', 'Honeywell'), ('Cm-moisture tester', 'Merck')]
    assert choose(noisy, strict=True) == ('Water', []) and choose(noisy)[1] == ['Cm-moisture tester']


def add(db, brand: str, number: str, name: str, cas: str, path: str = 'reagents', **extra) -> Product:
    brand_row = db.scalar(select(Brand).where(Brand.slug == brand))
    product = Product(brand_id=brand_row.id, catalog_number=number, catalog_number_norm=number.lower().replace('-', ''),
                      slug=f'{brand}-{number.lower()}', name_en=name, cas=cas, status='published', **extra)
    db.add(product)
    db.flush()
    category = db.scalar(select(Category).where(Category.path == path))
    db.add(ProductCategory(product_id=product.id, category_id=category.id, is_primary=True))
    return product


def test_the_build_makes_pages_for_cas_numbers_several_brands_sell(seeded):
    with seeded.begin() as db:
        add(db, 'macklin', 'T-1', '5-TERT-BUTYL-O-ANISIDINE, 97%', ANILINE)
        add(db, 'aozeal', 'A-1', '5-tert-Butyl-2-methoxyaniline, 97%', ANILINE)
        add(db, 'aozeal', 'A-2', 'Aozeal A-2', ANILINE)  # a stand-in name counts as an offer, not as a name
        # One brand only: no page, whatever the number of cards.
        for i in range(4):
            add(db, 'macklin', f'O-{i}', 'Only One Brand Chemical', '1000-00-1')
        # A precursor (any product of the CAS on the lists) never gets a page.
        add(db, 'macklin', 'P-1', 'Acetone', '67-64-1', controlled='IV')
        add(db, 'aozeal', 'P-2', 'Acetone', '67-64-1')
        add(db, 'trc', 'P-3', 'Acetone', '67-64-1')
        # Caffeine has its own written page.
        add(db, 'macklin', 'C-1', 'Caffeine', '58-08-2')
        add(db, 'aozeal', 'C-2', 'Caffeine', '58-08-2')
    counts = cas_pages.build(seeded)
    with seeded() as db:
        rows = {row.cas: row for row in db.scalars(select(CasPage))}
    page = rows[ANILINE]
    assert page.name == '5-tert-Butyl-2-methoxyaniline' and page.synonyms == ['5-tert-butyl-o-anisidine']
    assert page.offers == 3 and page.brands == ['Aozeal', 'Macklin'] and page.sections == ['reagents']
    assert not {'1000-00-1', '67-64-1', '58-08-2'} & set(rows)
    assert counts['added'] == len(rows)
    # A second build changes nothing; a page whose offers fall under the minimum goes.
    again = cas_pages.build(seeded)
    assert again['added'] == again['changed'] == again['removed'] == 0
    with seeded.begin() as db:
        db.scalar(select(Product).where(Product.slug == 'aozeal-a-2')).status = 'archived'
    assert cas_pages.build(seeded)['removed'] == 1


def test_the_page_its_link_from_the_card_and_the_sitemap(client, seeded):
    with seeded.begin() as db:
        add(db, 'macklin', 'T-1', '5-TERT-BUTYL-O-ANISIDINE, 97%', ANILINE)
        add(db, 'aozeal', 'A-1', '5-tert-Butyl-2-methoxyaniline, 97%', ANILINE)
        add(db, 'aozeal', 'A-3', '5-tert-Butyl-2-methoxyaniline', ANILINE)
    cas_pages.build(seeded)
    data = client.get(f'{URL}/cas/{ANILINE}').json()
    assert data['page']['name'] == '5-tert-Butyl-2-methoxyaniline' and data['page']['offers'] == 3
    assert len(data['items']) == 3 and data['sections'][0]['path'] == 'reagents'
    assert client.get(f'{URL}/cas/1000-00-1').status_code == 404
    # A substance with its own page sends the storefront there.
    assert client.get(f'{URL}/cas/58-08-2').json()['substance'] == 'caffeine'
    card = client.get(f'{URL}/products/aozeal-a-1').json()
    assert card['casPage'] == {'cas': ANILINE, 'name': '5-tert-Butyl-2-methoxyaniline', 'offers': 3}
    sitemap = client.get(f'{URL}/cas/sitemap').json()
    assert ANILINE in {i['cas'] for i in sitemap['items']} and sitemap['pageCount'] == 1
    # A hidden category takes its offers off the page at the next build.
    with seeded.begin() as db:
        set_setting(db, 'hidden_categories', ['reagents'])
    cas_pages.build(seeded)
    assert client.get(f'{URL}/cas/{ANILINE}').status_code == 404


def test_the_build_runs_once_a_night(seeded):
    night = datetime(2026, 11, 2, 2, 0, tzinfo=UTC)
    with seeded() as db:
        assert cas_pages.due(db, night) and not cas_pages.due(db, night.replace(hour=12))
    with seeded.begin() as db:
        set_setting(db, 'cas_pages_built_at', night.replace(hour=1).isoformat())
    with seeded() as db:
        assert not cas_pages.due(db, night)
        assert cas_pages.due(db, night.replace(day=3))


def test_search_offers_the_substance_page_for_a_cas_or_its_beginning(sessions):
    """Business remark of 3 November 2026: «Большинство знает только CAS и ищут по нему варианты»."""
    from app.catalog.search.query import cas_pages_for

    with sessions.begin() as db:
        db.add_all([CasPage(cas='67-56-1', name='Methanol', offers=509, brands=['Merck']),
                    CasPage(cas='67-52-7', name='Barbituric acid', offers=12, brands=['Merck']),
                    CasPage(cas='675-20-7', name='2-Piperidinone', offers=40, brands=['Merck']),
                    CasPage(cas='7664-38-2', name='ortho-Phosphoric acid', offers=122, brands=['Merck'])])
    with sessions() as db:
        assert [row['cas'] for row in cas_pages_for(db, '67-56-1')] == ['67-56-1']
        assert cas_pages_for(db, '67561') == [{'cas': '67-56-1', 'name': 'Methanol', 'offers': 509}]
        # The beginning with its hyphens: «67-5» is not «675-…».
        assert [row['cas'] for row in cas_pages_for(db, '67-5')] == ['67-56-1', '67-52-7']
        assert [row['cas'] for row in cas_pages_for(db, '675-')] == ['675-20-7']
        assert cas_pages_for(db, '7664-35') == [] and cas_pages_for(db, '67') == []
        # The digits of «7664-38» also make the valid CAS 766-43-8: the hyphens typed decide.
        assert [row['cas'] for row in cas_pages_for(db, '7664-38')] == ['7664-38-2']
        assert cas_pages_for(db, 'methanol') == [] and cas_pages_for(db, '67-56-2') == []
