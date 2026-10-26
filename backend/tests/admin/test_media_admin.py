"""Photos and documents of cards uploaded in the admin panel."""

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64
PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def test_a_photo_and_a_document_are_stored_and_served(client, signed_in):
    catalog = signed_in('catalog')
    photo = catalog.ok(catalog.post('/media', files={'file': ('фото.png', PNG, 'image/png')}))
    assert photo['url'].startswith('/api/v1/media/photos/') and photo['url'].endswith('.png')
    served = client.get(photo['url'])
    assert served.status_code == 200 and served.content == PNG and served.headers['content-type'] == 'image/png'
    document = catalog.ok(catalog.post('/media', files={'file': ('SDS.pdf', PDF, 'application/pdf')}))
    assert document['url'].startswith('/api/v1/media/documents/')
    # The same file twice is one file.
    assert catalog.ok(catalog.post('/media', files={'file': ('copy.png', PNG, 'image/png')}))['url'] == photo['url']


def test_scripts_and_other_types_are_refused(signed_in):
    catalog = signed_in('catalog')
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert catalog.post('/media', files={'file': ('x.svg', svg, 'image/svg+xml')}).status_code == 422
    assert catalog.post('/media', files={'file': ('x.png', b'<html>', 'image/png')}).status_code == 422
    assert catalog.post('/media', files={'file': ('x.pdf', b'%PDF-1.4 no end', 'application/pdf')}).status_code == 422
    assert signed_in('viewer').post('/media', files={'file': ('x.png', PNG, 'image/png')}).status_code == 403
