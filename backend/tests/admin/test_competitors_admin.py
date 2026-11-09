"""The admin panel: where a supplier keeps a product (its editor) and the state of the check."""

from app.catalog import competitors
from tests.catalog.test_competitors import catalog, sites  # noqa: F401 — the fake sites and the small catalog


def test_the_admin_editor_shows_where_a_supplier_keeps_the_product(sessions, sites, catalog, signed_in):  # noqa: F811
    competitors.run_all(sessions)
    admin = signed_in('admin')
    card = admin.ok(admin.get(f'/products/{catalog["sigma-base"]}'))
    assert card['supplierStock'] is True
    assert {(o['sourceName'], o['catalogNumber']) for o in card['supplierOffers']} == {
        ('Химмед', 'T5648-1G'), ('Химмед', 'T5648-5G')}
    assert all(o['url'].startswith('https://chimmed-new.ru/products/') for o in card['supplierOffers'])
    state = admin.ok(admin.get('/competitors'))
    assert state['productsInStock'] == 6 and state['last']['sources']['skygen']['complete']


def test_check_now_is_for_the_administrator(sessions, sites, catalog, signed_in):  # noqa: F811
    competitors.run_all(sessions)
    assert signed_in('viewer').post('/competitors/check').status_code == 403
    admin = signed_in('admin')
    state = admin.ok(admin.post('/competitors/check'))
    assert state['due'] is True
    with sessions() as db:
        assert competitors.due(db)
