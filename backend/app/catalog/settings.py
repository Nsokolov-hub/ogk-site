"""Settings of the site kept in the database and edited in the admin panel (ADM-06, ADM-07, ADM-09, ADM-10);
defaults until someone changes them."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import CatalogSetting

SITE: dict[str, Any] = {
    "ru": {
        "siteUrl": "https://www.ogk-chem.ru",
        "phone": {
            "display": "+7 495 234 28 63",
            "href": "tel:+74952342863"
        },
        "emails": {
            "info": "info@ogk-chem.ru",
            "order": "order@ogk-chem.ru"
        },
        "address": {
            "postalCode": "129301",
            "city": "Москва",
            "street": "ул. Касаткина, д. 8, помещ. 1/1",
            "full": "129301, Москва, ул. Касаткина, д. 8, помещ. 1/1",
            "mapQuery": "129301, Москва, ул. Касаткина, д. 8"
        },
        "hours": "пн–пт 9:00–18:00",
        "legal": {
            "name": "ООО «ОГК-ХИМ»",
            "shortName": "ОГК-ХИМ",
            "inn": "9717188828",
            "kpp": "771701001",
            "ogrn": "1267700023997"
        },
        "docs": {
            "consent": "/files/soglasie.pdf",
            "privacy": "/files/politika.pdf",
            "card": "/files/kartochka.pdf"
        }
    },
    "en": {
        "siteUrl": "https://www.ogk-chem.ru",
        "phone": {
            "display": "+7 495 234 28 63",
            "href": "tel:+74952342863"
        },
        "emails": {
            "info": "info@ogk-chem.ru",
            "order": "order@ogk-chem.ru"
        },
        "address": {
            "postalCode": "129301",
            "city": "Moscow",
            "street": "8 Kasatkina St., premises 1/1",
            "full": "8 Kasatkina St., premises 1/1, Moscow 129301, Russia",
            "mapQuery": "129301, Москва, ул. Касаткина, д. 8"
        },
        "hours": "Mon–Fri 9:00–18:00 (Moscow time)",
        "legal": {
            "name": "OGK-CHEM LLC",
            "shortName": "OGK-CHEM",
            "inn": "9717188828",
            "kpp": "771701001",
            "ogrn": "1267700023997"
        },
        "docs": {
            "consent": "/files/soglasie.pdf",
            "privacy": "/files/politika.pdf",
            "card": "/files/kartochka.pdf"
        }
    }
}

DEFAULTS: dict[str, Any] = {
    # TZ 5.6: weights of completeness and the threshold of indexing; the starting threshold is 70.
    'completeness_weights': {'identity': 20, 'image': 15, 'description': 25, 'document': 15, 'link': 10,
                             'storage': 15},
    'index_threshold': 70,
    # TZ 5.2.1: products of the lists are hidden from the storefront, search, Sitemap and the feed.
    'hide_controlled': True,
    # TZ 15.4: categories (path prefixes) and brands of the Yandex Direct feed; empty brands — all.
    'feed': {'categories': ['reference-standards', 'chromatography', 'reagents', 'biological-standards',
                            'laboratory-equipment'], 'brands': []},
    # Texts of the catalog root /catalog/: {"ru": CategoryContent, "en": CategoryContent}.
    'catalog_root': {},
    # Products of the home page block, by slug, in order.
    'home_products': [],
    # Flow F5: the newest change of the CRM registry already loaded, and when the last load ran.
    'brands_synced_at': None,
    'brands_sync_run_at': None,
    # Substance names or search synonyms changed: the worker sends the new synonyms to the index (SRCH-05).
    'search_settings_dirty': False,
    # ADM-10: contacts and requisites — one source for the header, the footer and Organization ({"ru", "en"}).
    'site': SITE,
    # ADM-10: counters (TZ 15.1); empty — the numbers from YM_COUNTER_ID and GA_MEASUREMENT_ID of the server.
    'counters': {'ym': None, 'ga': None},
    # SEO-02: meta templates of cards and substances; empty — the storefront's own (messages/*.json).
    # Placeholders: {name} {brand} {number} {cas} {ids} {logistics}; substances {name} {count} {brands}.
    'meta_templates': {'product': {'ru': {}, 'en': {}}, 'substance': {'ru': {}, 'en': {}}},
    # ADM-07: lines added to robots.txt of production after the required rules (SEO-03).
    'robots_extra': '',
    # ADM-06: search synonyms beyond the substances' names, pairs or groups of words (SRCH-05).
    'search_synonyms': [],
    # ADM-06: units of packagings and storage conditions with their names.
    'units': [{'key': 'mg', 'ru': 'мг', 'en': 'mg'}, {'key': 'g', 'ru': 'г', 'en': 'g'},
              {'key': 'kg', 'ru': 'кг', 'en': 'kg'}, {'key': 'ul', 'ru': 'мкл', 'en': 'µl'},
              {'key': 'ml', 'ru': 'мл', 'en': 'ml'}, {'key': 'l', 'ru': 'л', 'en': 'l'},
              {'key': 'pcs', 'ru': 'шт.', 'en': 'pcs'}, {'key': 'pack', 'ru': 'уп.', 'en': 'pack'}],
    'storage_conditions': [{'key': 'room', 'ru': 'Комнатная температура', 'en': 'Room temperature'},
                           {'key': '2-8', 'ru': '+2…+8 °C', 'en': '+2…+8 °C'},
                           {'key': '-20', 'ru': '−20 °C', 'en': '−20 °C'},
                           {'key': '-80', 'ru': '−80 °C', 'en': '−80 °C'}],
    # ADM-09: who gets the letters and the opening words of the customer letters; empty — the server's settings.
    'mail': {'sales_email': '', 'alert_emails': '', 'customer_intro_ru': '', 'customer_intro_en': ''},
}


def get_setting(db: Session, key: str) -> Any:
    row = db.scalar(select(CatalogSetting).where(CatalogSetting.key == key))
    return DEFAULTS[key] if row is None else row.value


def set_setting(db: Session, key: str, value: Any) -> None:
    if key not in DEFAULTS:
        raise KeyError(key)
    row = db.get(CatalogSetting, key)
    if row is None:
        db.add(CatalogSetting(key=key, value=value))
    else:
        row.value = value
    db.flush()
