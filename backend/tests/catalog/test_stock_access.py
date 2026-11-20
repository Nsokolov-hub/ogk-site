"""Public sources obey robots, explicit origins, redirects and refusals without alternate access."""

import httpx
import pytest

from app.catalog.stock_sources.base import PublicClient, Refused, Robots


def test_robots_matches_literal_query_wildcards_and_longest_allow():
    robots = Robots('''User-agent: *
Disallow: /?
Disallow: /*utm*=
Disallow: /wp-
Allow: /wp-content/uploads/
Disallow: /private$
''', 'StockCheck/1.0')
    assert robots.allowed('https://source.test/news/current/')
    assert not robots.allowed('https://source.test/?s=reagent')
    assert not robots.allowed('https://source.test/news/?utm_source=x')
    assert not robots.allowed('https://source.test/wp-admin/')
    assert robots.allowed('https://source.test/wp-content/uploads/stock.pdf')
    assert not robots.allowed('https://source.test/private')
    assert robots.allowed('https://source.test/private-public')


def test_robots_specific_agent_groups_and_allow_ties():
    robots = Robots('''User-agent: *
Disallow: /
User-agent: StockCheck
Disallow: /catalog/
Allow: /catalog/
''', 'Mozilla/5.0 (compatible; StockCheck/1.0)')
    assert robots.allowed('https://source.test/catalog/a/')
    assert robots.allowed('https://source.test/news/')
    assert not Robots('User-agent: *\nDisallow: /\nUser-agent: StockCheck\nDisallow:',
                      'StockCheck').rules


def test_robots_preserves_reserved_percent_encoded_separators():
    robots = Robots('User-agent: *\nDisallow: /catalog/a%2Fb\nDisallow: /catalog/%41', 'StockCheck')
    assert not robots.allowed('https://source.test/catalog/a%2fb')
    assert robots.allowed('https://source.test/catalog/a/b')
    assert not robots.allowed('https://source.test/catalog/A')


@pytest.mark.parametrize('status,body,reason', [
    (403, 'forbidden', '403'), (429, 'slow down', '429'),
    (503, '<form><div class="smartcaptcha"></div></form>', 'captcha'),
    (302, '', 'redirect_requires_review'),
])
def test_refusal_or_redirect_never_follows_another_endpoint(status, body, reason):
    requests = []

    def handle(request):
        requests.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /catalog/')
        return httpx.Response(status, text=body, headers={'Location': 'https://elsewhere.test/private'})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        public = PublicClient(client, 'https://source.test', 'StockCheck', ['/catalog/'])
        with pytest.raises(Refused, match=reason):
            public.get('https://source.test/catalog/a/')
    assert requests == ['https://source.test/robots.txt', 'https://source.test/catalog/a/']


def test_undeclared_origin_or_path_is_rejected_before_network():
    requests = []

    def handle(request):
        requests.append(str(request.url))
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        public = PublicClient(client, 'https://source.test', 'StockCheck', ['/catalog/'])
        with pytest.raises(Refused, match='origin_not_allowed'):
            public.get('https://elsewhere.test/catalog/')
        with pytest.raises(Refused, match='path_not_allowed'):
            public.get('https://source.test/account/')
    assert requests == ['https://source.test/robots.txt']
