"""The admin panel in tests: staff of every role, a signed-in client per role with its CSRF token."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.admin import security
from app.admin.models import StaffUser
from app.main import app as api

PASSWORD = 'correct-horse-battery-staple'


class Admin:
    """A signed-in staff member: every change carries the session's CSRF token, as the admin panel does."""

    def __init__(self, client: TestClient, me: dict[str, Any]):
        self.client, self.me = client, me
        self.headers = {'X-CSRF-Token': me['csrfToken']}

    def get(self, path: str, **kw: Any) -> Any:
        return self.client.get(f'/api/v1/admin{path}', **kw)

    def post(self, path: str, json: Any = None, **kw: Any) -> Any:
        return self.client.post(f'/api/v1/admin{path}', json=json, headers={**self.headers, **kw.pop('headers', {})},
                                **kw)

    def put(self, path: str, json: Any = None, **kw: Any) -> Any:
        return self.client.put(f'/api/v1/admin{path}', json=json, headers=self.headers, **kw)

    def patch(self, path: str, json: Any = None) -> Any:
        return self.client.patch(f'/api/v1/admin{path}', json=json, headers=self.headers)

    def delete(self, path: str) -> Any:
        return self.client.delete(f'/api/v1/admin{path}', headers=self.headers)

    def ok(self, response: Any) -> Any:
        assert response.status_code < 400, response.text
        return response.json()


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    """Each test signs in many times from one address: the per-minute limit starts empty."""
    from app.admin.routes import access
    from app.content import routes as content_routes
    from app.core.ratelimit import RateLimiter

    monkeypatch.setattr(access, 'login_limiter', RateLimiter('admin-login-test'))
    monkeypatch.setattr(content_routes, 'views_limiter', RateLimiter('views-test'))


@pytest.fixture
def staff(sessions) -> dict[str, StaffUser]:
    users = {}
    with sessions.begin() as db:
        for role in ('admin', 'content', 'catalog', 'viewer'):
            user = StaffUser(email=f'{role}@ogk-chem.ru', name=f'Сотрудник {role}', role=role,
                             password_hash=security.hash_password(PASSWORD))
            db.add(user)
            users[role] = user
    return users


@pytest.fixture
def signed_in(client, staff) -> Iterator[Callable[[str], Admin]]:
    """signed_in('content') — a client of its own, signed in with that role."""
    clients: list[TestClient] = []

    def make(role: str) -> Admin:
        test_client = TestClient(api)
        clients.append(test_client)
        response = test_client.post('/api/v1/admin/auth/login', json={'email': f'{role}@ogk-chem.ru',
                                                                     'password': PASSWORD})
        assert response.status_code == 200, response.text
        return Admin(test_client, response.json())

    yield make
    for test_client in clients:
        test_client.close()


@pytest.fixture
def admin(signed_in) -> Admin:
    return signed_in('admin')


@pytest.fixture
def seeded(sessions):
    """The test catalog and the site's texts (seed/catalog.json, seed/content.json)."""
    from app.catalog import seed
    from app.catalog.search import query

    with sessions.begin() as db:
        seed.load(db)
    query.reset_directory()
    return sessions
