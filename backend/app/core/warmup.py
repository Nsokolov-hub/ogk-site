"""Read-only warmup of the running API before replacing the storefront's populated cache."""

import json
from urllib.parse import quote, urlencode
from urllib.request import urlopen

ORIGIN = 'http://127.0.0.1:8000'


def warm() -> list[str]:
    checked: list[str] = []

    def get(path: str):
        with urlopen(ORIGIN + path, timeout=30) as response:
            result = json.load(response)
        checked.append(path.split('?')[0])
        return result

    get('/ready')
    get('/api/v1/public/catalog/tree')
    get('/api/v1/public/catalog/category')
    popular = get('/api/v1/public/catalog/popular?limit=1&lang=ru&sort=popular')
    # This initializes the process's search directories once, before a new web cache sends parallel reads.
    get('/api/v1/public/search/suggest?q=EDQM&lang=ru')
    if popular['items']:
        item = popular['items'][0]
        get('/api/v1/public/products/' + quote(item['slug'], safe=''))
        get('/api/v1/public/search?' + urlencode({'q': item['catalogNumber'], 'lang': 'ru'}))
        if item.get('cas'):
            get('/api/v1/public/cas/' + quote(item['cas'], safe=''))
    return checked


if __name__ == '__main__':
    print(json.dumps({'api_warmup': warm()}, ensure_ascii=False))
