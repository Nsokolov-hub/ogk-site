"""Search on a real Meilisearch with the control examples of TZ 6 (SRCH-01…SRCH-10) and category listings."""

from sqlalchemy import select

from app.catalog.models import Product, SearchMiss

URL = '/api/v1/public'


def suggest(client, q, lang='ru'):
    response = client.get(f'{URL}/search/suggest', params={'q': q, 'lang': lang})
    assert response.status_code == 200, response.text
    return response.json()


def test_exact_number_and_cas_come_first(client, meili):
    for q in ('Y0001897', 'y000-1897', 'Y 000 1897'):
        found = suggest(client, q)
        assert found['items'][0]['catalogNumber'] == 'Y0001897' and found['items'][0]['brand'] == 'EDQM', q
        assert found['items'][0]['match'] == 'catalogNumber'
    for q in ('28721-07-5', '28721075'):
        first = suggest(client, q)['items'][0]
        assert (first['catalogNumber'], first['match']) == ('Y0001897', 'cas')
    assert suggest(client, '28721-07-5')['substances'][0]['slug'] == 'oxcarbazepine'


def test_names_russian_synonyms_layout_and_formula(client, meili):
    assert suggest(client, 'oxcarb')['items'][0]['name'].startswith('Oxcarbazepine')
    russian = suggest(client, 'окскарбазепин')
    assert russian['items'] and all('carbazepine' in i['name'].lower() for i in russian['items'][:3])
    layout = suggest(client, 'jrcrfh,fptgby')
    assert layout['corrected'] == 'окскарбазепин' and layout['items']
    formula = suggest(client, 'C15H12N2O2')
    assert formula['items'][0]['match'] == 'formula' and formula['items'][0]['formula'] == 'C15H12N2O2'
    assert suggest(client, 'x')['items'] == []


def test_search_page_facets_and_demand_without_product(client, meili, sessions):
    page = client.get(f'{URL}/search', params={'q': 'paracetamol'}).json()
    assert page['total'] >= 3 and page['items'][0]['name'] == 'Paracetamol CRS'
    brands = {v['value']: v['count'] for v in page['facets']['brand']}
    assert brands['edqm'] >= 1 and page['facets']['category'][0]['value'] == 'reference-standards'
    narrowed = client.get(f'{URL}/search', params={'q': 'paracetamol', 'brand': 'usp'}).json()
    assert {p['brand']['slug'] for p in narrowed['items']} == {'usp'}
    # Counts of the brand facet ignore its own selection: the alternatives stay visible.
    assert len(narrowed['facets']['brand']) == len(page['facets']['brand'])
    empty = client.get(f'{URL}/search', params={'q': 'несуществующий стандарт xyz'}).json()
    assert empty['total'] == 0
    with sessions() as db:
        assert db.scalar(select(SearchMiss.count).where(SearchMiss.query == 'несуществующий стандарт xyz')) == 1


def test_category_listing_with_disjunctive_facets(client, meili):
    base = client.get(f'{URL}/catalog/listing', params={'path': 'reference-standards', 'facets': 'brand,pack,storage'})
    listing = base.json()
    assert listing['total'] > 50 and base.headers['cache-control'].startswith('public')
    brands = {v['value']: v['count'] for f in listing['facets'] if f['key'] == 'brand' for v in f['values']}
    filtered = client.get(f'{URL}/catalog/listing', params={'path': 'reference-standards', 'facets': 'brand,pack',
                                                          'f.brand': 'edqm'}).json()
    assert filtered['total'] == brands['edqm']
    assert {p['brand']['slug'] for p in filtered['items']} == {'edqm'}
    brand_facet = next(f for f in filtered['facets'] if f['key'] == 'brand')
    assert {v['value']: v['count'] for v in brand_facet['values']} == brands
    by_name = client.get(f'{URL}/catalog/listing', params={'path': 'reference-standards', 'sort': 'name'}).json()
    names = [p['name'].casefold() for p in by_name['items']]
    assert names == sorted(names)
    pack = next(f for f in listing['facets'] if f['key'] == 'pack')
    assert any(v['label'] == '100 мг' for v in pack['values'])
    assert client.get(f'{URL}/catalog/count', params={'path': 'chromatography/hplc-columns',
                                                     'p.brand': 'waters', 'p.phase': 'C18'}).json()['count'] >= 3


def test_controlled_products_are_hidden(client, meili, sessions):
    with sessions() as db:
        hidden = db.scalars(select(Product.catalog_number).where(Product.controlled.is_not(None))).all()
    assert hidden
    for number in hidden:
        assert suggest(client, number)['total'] == 0


def test_list_search_statuses(client, meili):
    lines = ['Y0001897 2', '28721-07-5;3', 'Paracetamol', 'nothing-here-xyz', '']
    answer = client.post(f'{URL}/search/batch', json={'lines': lines}).json()
    statuses = [(r['query'], r['status'], r['quantity']) for r in answer['lines']]
    assert statuses[0] == ('Y0001897', 'exact', 2) and statuses[1] == ('28721-07-5', 'exact', 3)
    assert statuses[2][1] == 'multiple' and statuses[3][1] == 'none' and len(statuses) == 4


def test_list_search_from_a_file(client, meili, tmp_path):
    from app.catalog.importer.run import write_xlsx

    path = tmp_path / 'list.xlsx'
    write_xlsx(path, [['Кат. №', 'Количество'], ['Y0001897', 2], ['P0300000', 1]])
    answer = client.post(f'{URL}/search/batch/file', files={'file': ('list.xlsx', path.read_bytes())}).json()
    assert [(r['query'], r['status']) for r in answer['lines']][1:] == [('Y0001897', 'exact'), ('P0300000', 'exact')]
    bad = client.post(f'{URL}/search/batch/file', files={'file': ('list.pdf', b'%PDF')})
    assert bad.status_code == 422 and bad.json()['code'] == 'FILE_UNREADABLE'
