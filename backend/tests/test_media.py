"""Files of the site (local disk or S3) and 2D structures drawn from SMILES, served at /api/v1/media/…."""

import io

import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber
from sqlalchemy import select

from app.catalog import structures
from app.catalog.models import Brand, Product
from app.core import files
from app.outbox import worker

PARACETAMOL = 'CC(=O)Nc1ccc(O)cc1'


def test_local_storage_keeps_files_private_and_refuses_odd_keys(tmp_path):
    store = files.LocalStorage(tmp_path)
    store.put('media/x/a.svg', b'<svg/>', 'image/svg+xml')
    assert store.get('media/x/a.svg') == b'<svg/>' and store.exists('media/x/a.svg')
    assert (tmp_path / 'media/x/a.svg').stat().st_mode & 0o077 == 0
    for key in ('../etc/passwd', '/abs', 'media/../../x', 'Media/X.svg', ''):
        with pytest.raises(files.FileMissing):
            store.get(key)
    store.delete('media/x/a.svg')
    assert not store.exists('media/x/a.svg')


def test_s3_storage_speaks_to_the_bucket():
    import boto3

    client = boto3.client('s3', region_name='ru-central1', endpoint_url='https://storage.example',
                          aws_access_key_id='k', aws_secret_access_key='s')
    store = files.S3Storage(client, 'ogk-files', 'staging')
    with Stubber(client) as stub:
        stub.add_response('put_object', {}, {'Bucket': 'ogk-files', 'Key': 'staging/media/a.svg', 'Body': b'<svg/>',
                                             'ContentType': 'image/svg+xml'})
        stub.add_response('get_object', {'Body': StreamingBody(io.BytesIO(b'<svg/>'), 6)},
                          {'Bucket': 'ogk-files', 'Key': 'staging/media/a.svg'})
        stub.add_client_error('get_object', 'NoSuchKey', http_status_code=404)
        stub.add_client_error('head_object', '404', http_status_code=404)
        stub.add_client_error('put_object', 'InternalError', http_status_code=500)
        store.put('media/a.svg', b'<svg/>', 'image/svg+xml')
        assert store.get('media/a.svg') == b'<svg/>'
        with pytest.raises(files.FileMissing):
            store.get('media/b.svg')
        assert store.exists('media/b.svg') is False
        with pytest.raises(files.StorageUnavailable):
            store.put('media/c.svg', b'x', 'image/svg+xml')


def card(sessions, **fields) -> str:
    with sessions.begin() as db:
        brand = db.scalar(select(Brand).where(Brand.slug == 'edqm'))
        if brand is None:
            brand = Brand(slug='edqm', name='EDQM', content={})
            db.add(brand)
            db.flush()
        number = fields.pop('number', 'Y0000001')
        product = Product(brand_id=brand.id, catalog_number=number, catalog_number_norm=number.lower(),
                          slug=f'edqm-{number.lower()}', name_en='Paracetamol', name_ru='Парацетамол', **fields)
        db.add(product)
        db.flush()
        return product.id


def test_structures_are_drawn_once_shared_and_served(client, sessions):
    first = card(sessions, smiles=PARACETAMOL)
    twin = card(sessions, smiles=PARACETAMOL, number='Y0000002')
    photo = card(sessions, smiles=PARACETAMOL, number='Y0000003',
                 images=[{'src': '/images/x.jpg', 'alt': 'Фото', 'kind': 'photo'}])
    broken = card(sessions, smiles='C1CC(', number='Y0000004')
    with sessions.begin() as db:
        assert structures.draw_pending(db) == 2
    with sessions() as db:
        image = db.get(Product, first).images[0]
        assert image['kind'] == 'structure' and image['alt'] == 'Структурная формула: Парацетамол'
        assert db.get(Product, twin).images[0]['src'] == image['src']
        assert db.get(Product, photo).images[0]['kind'] == 'photo'
        assert db.get(Product, broken).images == [] and db.get(Product, broken).structure_smiles == 'C1CC('
        assert db.get(Product, first).needs_index is True
    # Nothing left in the queue: nothing is drawn twice.
    with sessions.begin() as db:
        assert structures.draw_pending(db) == 0
    answer = client.get(image['src'])
    assert answer.status_code == 200 and answer.headers['content-type'] == 'image/svg+xml'
    assert answer.content.startswith(b'<svg') and b'#E7E7E7' in answer.content and b'<script' not in answer.content
    assert 'immutable' in answer.headers['cache-control'] and 'sandbox' in answer.headers['content-security-policy']
    assert client.get('/api/v1/media/structures/00/missing.svg').status_code == 404
    assert client.get('/api/v1/media/structures/x.html').status_code == 404
    assert client.get('/api/v1/media/..%2F..%2Fattachments/x.pdf').status_code == 404
    # A new SMILES is drawn again; a removed one takes its picture away.
    with sessions.begin() as db:
        db.get(Product, first).smiles = 'CC(=O)Oc1ccccc1C(=O)O'
        db.get(Product, twin).smiles = None
    with sessions.begin() as db:
        assert structures.draw_pending(db) == 2
    with sessions() as db:
        assert db.get(Product, first).images[0]['src'] != image['src']
        assert db.get(Product, twin).images == []


def test_the_worker_draws_before_indexing(sessions, monkeypatch):
    monkeypatch.setattr(worker, 'SessionLocal', sessions)
    product_id = card(sessions, smiles=PARACETAMOL)
    assert worker.draw_structures() == 1
    with sessions() as db:
        assert db.get(Product, product_id).images[0]['kind'] == 'structure'
