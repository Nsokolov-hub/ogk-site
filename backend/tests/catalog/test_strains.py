import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.catalog.models import Category, Packaging, Product
from app.catalog.strains import StrainRecord, import_reviewed

MANIFEST = Path(__file__).parents[2] / 'app/catalog/data/strains-2026-11-27.json'


def record():
    return next(row for row in json.loads(MANIFEST.read_text())['products'] if row['article'] == '0335P')


def test_verified_manifest_uses_manufacturer_articles_and_reference_codes_separately():
    rows = [StrainRecord.model_validate(row) for row in json.loads(MANIFEST.read_text())['products']]
    assert len(rows) == len({(row.manufacturer, row.article) for row in rows}) == 82
    ecoli = next(row for row in rows if row.article == 'R4607050')
    assert ecoli.strain_code == 'ATCC 25922'
    assert ecoli.pack_count == 5
    assert record()['pack_count'] == 2


def test_strain_import_is_repeatable_and_public_search_keeps_both_identifiers(sessions, client):
    with sessions.begin() as db:
        db.add(Category(slug='biological-standards', path='biological-standards', name_ru='Микроорганизмы'))
        db.flush()
        result = import_reviewed(db, [record()])
        assert result['created'] == 1
        row = db.get(Product, result['products'][0]['id'])
        assert row.catalog_number == '0335P'
        assert row.attributes['strain_code'] == ['ATCC 25922']
        assert row.availability == 'on_order'
        assert row.status == 'published'
        slug = row.slug
        assert import_reviewed(db, [record()])['created'] == 0
        assert db.scalar(select(func.count()).select_from(Product)) == 1
        assert db.scalar(select(func.count()).select_from(Packaging)) == 1
    response = client.get(f'/api/v1/public/products/{slug}')
    assert response.status_code == 200, response.text
    product = response.json()['product']
    assert product['catalogNumber'] == '0335P'
    assert product['attributes']['strain_code'] == ['ATCC 25922']
    assert product['packagings'][0]['label'] == '2 устройства KWIK-STIK'


@pytest.mark.parametrize('case', ['duplicate', 'external_source'])
def test_strain_import_rejects_unreviewed_identity_records_before_writing(sessions, case):
    rows = [record()]
    if case == 'duplicate':
        rows += [record()]
    else:
        rows[0]['source_url'] = 'https://unverified.test/0335P'
    with sessions.begin() as db:
        with pytest.raises(ValueError):
            import_reviewed(db, rows)
        assert db.scalar(select(func.count()).select_from(Product)) == 0
