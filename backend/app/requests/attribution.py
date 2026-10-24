"""Where the customer came from (TZ 15.3).

The storefront middleware keeps the first and the last touch in the first-party cookie `ogk_attr` for 90 days;
the API reads it together with the ClientID cookies of Yandex Metrica and GA4 when a request is sent, so the
chain «Яндекс → статья → EDQM → товар → заявка через неделю» reaches the CRM (contract F1).
"""

import base64
import binascii
import json
from typing import Any
from urllib.parse import urlparse

COOKIE = 'ogk_attr'
TOUCH_FIELDS = ('landing_url', 'referrer', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
                'yclid', 'gclid', 'at')
PAID_MEDIUMS = {'cpc', 'ppc', 'paid', 'cpm', 'cpa', 'display', 'banner', 'retargeting'}
EMAIL_MEDIUMS = {'email', 'e-mail', 'newsletter', 'mail'}
SOCIAL_MEDIUMS = {'social', 'smm', 'social-network', 'socialnetwork'}
SOCIAL_SOURCES = {'vk', 'vkontakte', 'telegram', 'tg', 't.me', 'ok', 'odnoklassniki', 'facebook', 'instagram',
                  'dzen', 'youtube', 'rutube', 'linkedin'}
SEARCH_HOSTS = ('yandex.', 'ya.ru', 'google.', 'bing.com', 'go.mail.ru', 'duckduckgo.com', 'search.yahoo.')
SOCIAL_HOSTS = ('vk.com', 't.me', 'telegram.', 'ok.ru', 'facebook.com', 'instagram.com', 'dzen.ru', 'youtube.com',
                'rutube.ru', 'linkedin.com')
OWN_HOSTS = ('ogk-chem.ru',)


def clean_touch(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    touch = {key: str(value[key])[:2000 if key in ('landing_url', 'referrer') else 250]
             for key in TOUCH_FIELDS if isinstance(value.get(key), str) and value[key].strip()}
    return touch or None


def read_cookie(raw: str | None) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    """(first touch, last touch) from the cookie; a damaged cookie is treated as absent."""
    if not raw:
        return None, None
    try:
        padded = raw + '=' * (-len(raw) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    return clean_touch(data.get('first')), clean_touch(data.get('last'))


def host_of(url: str | None) -> str:
    try:
        return (urlparse(url or '').hostname or '').lower()
    except ValueError:
        return ''


def channel(touch: dict[str, str] | None) -> str:
    """cpc, organic, referral, direct, email or social — rules of TZ 15.3."""
    if not touch:
        return 'direct'
    medium = touch.get('utm_medium', '').lower()
    source = touch.get('utm_source', '').lower()
    if touch.get('yclid') or touch.get('gclid') or medium in PAID_MEDIUMS:
        return 'cpc'
    if medium in EMAIL_MEDIUMS:
        return 'email'
    if medium in SOCIAL_MEDIUMS or source in SOCIAL_SOURCES:
        return 'social'
    if medium == 'organic':
        return 'organic'
    if medium in ('referral', 'partner'):
        return 'referral'
    host = host_of(touch.get('referrer'))
    if host and not any(host == own or host.endswith('.' + own) for own in OWN_HOSTS):
        if any(mark in host for mark in SEARCH_HOSTS):
            return 'organic'
        if any(host == social or host.endswith('.' + social) or social in host for social in SOCIAL_HOSTS):
            return 'social'
        return 'referral'
    if source:
        return 'referral'
    return 'direct'


def ga_client_id(raw: str | None) -> str | None:
    """`_ga` = GA1.1.1234567890.1698765432 → 1234567890.1698765432."""
    parts = (raw or '').split('.')
    return '.'.join(parts[-2:]) if len(parts) >= 4 and all(part.isdigit() for part in parts[-2:]) else None


def collect(cookies: dict[str, str], conversion_page_url: str | None) -> dict[str, Any]:
    """The attribution block of contract F1."""
    first, last = read_cookie(cookies.get(COOKIE))
    ym_uid = cookies.get('_ym_uid')
    return {
        'first_touch': first,
        'last_touch': last,
        'conversion_page_url': conversion_page_url,
        'channel': channel(last or first),
        'client_ids': {
            'ym_uid': ym_uid[:100] if ym_uid and ym_uid.isdigit() else None,
            'ga_client_id': ga_client_id(cookies.get('_ga')),
        },
    }
