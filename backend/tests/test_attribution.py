"""Channel rules of TZ 15.3 and reading the attribution cookie."""

import pytest

from app.requests.attribution import channel, collect, ga_client_id, read_cookie
from tests.support import attribution_cookie


@pytest.mark.parametrize('touch, expected', [
    ({'utm_source': 'yandex', 'utm_medium': 'cpc'}, 'cpc'),
    ({'yclid': '123'}, 'cpc'),
    ({'gclid': 'abc', 'referrer': 'https://www.google.com/'}, 'cpc'),
    ({'utm_source': 'sendpulse', 'utm_medium': 'email'}, 'email'),
    ({'utm_source': 'vk'}, 'social'),
    ({'referrer': 'https://t.me/some_channel'}, 'social'),
    ({'referrer': 'https://yandex.ru/search/?text=edqm'}, 'organic'),
    ({'referrer': 'https://www.google.com/'}, 'organic'),
    ({'utm_source': 'yandex', 'utm_medium': 'organic'}, 'organic'),
    ({'referrer': 'https://pharm-portal.example/distributors'}, 'referral'),
    ({'referrer': 'https://www.ogk-chem.ru/catalog/'}, 'direct'),
    ({'landing_url': 'https://www.ogk-chem.ru/'}, 'direct'),
    (None, 'direct'),
])
def test_channel(touch, expected):
    assert channel(touch) == expected


def test_damaged_cookie_is_ignored():
    assert read_cookie('not-base64-json!') == (None, None)
    assert read_cookie(None) == (None, None)


def test_first_touch_survives_and_last_decides_the_channel():
    cookie = attribution_cookie({'referrer': 'https://ya.ru/', 'landing_url': 'https://www.ogk-chem.ru/articles/x/'},
                                {'utm_source': 'yandex', 'utm_medium': 'cpc', 'utm_campaign': 'edqm'})
    block = collect({'ogk_attr': cookie}, 'https://www.ogk-chem.ru/rfq/')
    assert block['first_touch']['referrer'] == 'https://ya.ru/'
    assert block['last_touch']['utm_campaign'] == 'edqm'
    assert block['channel'] == 'cpc'
    assert block['conversion_page_url'] == 'https://www.ogk-chem.ru/rfq/'


def test_ga_client_id():
    assert ga_client_id('GA1.1.1234567890.1698765432') == '1234567890.1698765432'
    assert ga_client_id('garbage') is None
