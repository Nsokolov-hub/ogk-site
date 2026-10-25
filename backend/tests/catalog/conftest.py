"""Catalog fixtures: the seed catalog in the test database and, with TEST_MEILI_URL, a throwaway search index."""

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest

from app.catalog import seed
from app.catalog.routes import get_engine
from app.catalog.search import indexer, query
from app.catalog.search.meili import Meilisearch
from app.core.config import settings
from app.main import app as api


@pytest.fixture
def seeded(sessions):
    with sessions.begin() as db:
        seed.load(db)
    query.reset_directory()
    return sessions


@pytest.fixture
def meili(seeded, monkeypatch) -> Iterator[Meilisearch]:
    """The seed catalog indexed in a fresh index of a real Meilisearch (TEST_MEILI_URL, TEST_MEILI_KEY)."""
    url = os.environ.get('TEST_MEILI_URL')
    if not url:
        pytest.skip('TEST_MEILI_URL не задан: тесты поиска идут на настоящем Meilisearch')
    engine = Meilisearch(url, os.environ.get('TEST_MEILI_KEY', settings.meili_key), timeout=30)
    monkeypatch.setattr(settings, 'meili_index', f'test_{uuid4().hex[:12]}')
    with seeded.begin() as db:
        indexer.configure(db, engine)
    while True:
        with seeded.begin() as db:
            if not indexer.index_pending(db, engine):
                break
    engine.wait(60)
    api.dependency_overrides[get_engine] = lambda: engine
    try:
        yield engine
    finally:
        api.dependency_overrides.pop(get_engine, None)
        engine.drop(settings.meili_index)
