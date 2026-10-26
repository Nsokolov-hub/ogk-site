"""Test database: in-memory SQLite by default, a throwaway PostgreSQL schema with TEST_DATABASE_URL."""

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateSchema, DropSchema

import app.models  # noqa: F401
from app.core.config import settings
from app.core.db import Base, get_db
from app.main import app as api


@pytest.fixture
def engine() -> Iterator[Engine]:
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        yield engine
        engine.dispose()
        return
    schema = f'test_{uuid4().hex}'
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema} -ctimezone=UTC'})
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


@pytest.fixture
def sessions(engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'storage_dir', tmp_path / 'files')
    monkeypatch.setattr(settings, 'smtp_host', '')
    monkeypatch.setattr(settings, 'telegram_bot_token', '')
    monkeypatch.setattr(settings, 'smartcaptcha_server_key', '')
    monkeypatch.setattr(settings, 'crm_url', 'https://crm.test')
    monkeypatch.setattr(settings, 'crm_token', 'ogk_site_test-token')
    monkeypatch.setattr(settings, 'crm_signing_secret', 'test-signing-secret')
    monkeypatch.setattr(settings, 'crm_delivery_enabled', True)


@pytest.fixture
def client(sessions) -> Iterator[TestClient]:
    def session() -> Iterator[Session]:
        with sessions() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    api.dependency_overrides[get_db] = session
    try:
        with TestClient(api) as test_client:
            yield test_client
    finally:
        api.dependency_overrides.pop(get_db, None)
