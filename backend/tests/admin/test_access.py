"""Sign-in, the second factor, CSRF, roles and staff accounts (ADM-01)."""

import pyotp
from sqlalchemy import select

from app.admin import security
from app.admin.models import AuditEntry, StaffUser
from app.core.config import settings
from tests.admin.conftest import PASSWORD


def test_login_sets_an_http_only_cookie_and_returns_rights(client, staff):
    response = client.post('/api/v1/admin/auth/login', json={'email': 'Content@OGK-chem.ru', 'password': PASSWORD})
    assert response.status_code == 200, response.text
    me = response.json()
    assert me['role'] == 'content' and 'pages.write' in me['permissions'] and 'requests.pii' not in me['permissions']
    cookie = response.headers['set-cookie']
    assert 'ogk_admin=' in cookie and 'HttpOnly' in cookie and 'Path=/api/v1/admin' in cookie
    assert 'samesite=strict' in cookie.lower()
    assert client.get('/api/v1/admin/auth/me').json()['email'] == 'content@ogk-chem.ru'


def test_wrong_passwords_lock_the_account(client, staff, sessions):
    for _ in range(10):
        response = client.post('/api/v1/admin/auth/login', json={'email': 'viewer@ogk-chem.ru', 'password': 'nope'})
        assert response.status_code == 401
    locked = client.post('/api/v1/admin/auth/login', json={'email': 'viewer@ogk-chem.ru', 'password': PASSWORD})
    assert locked.status_code == 429 and locked.json()['code'] == 'ACCOUNT_LOCKED'
    with sessions() as db:
        assert db.scalar(select(StaffUser.locked_until).where(StaffUser.email == 'viewer@ogk-chem.ru')) is not None


def test_changes_need_the_csrf_token_and_the_admin_origin(admin):
    body = {'email': 'new@ogk-chem.ru', 'name': 'Новый', 'role': 'viewer', 'password': 'long-enough-password'}
    bare = admin.client.post('/api/v1/admin/users', json=body)
    assert bare.status_code == 403 and bare.json()['code'] == 'CSRF_INVALID'
    foreign = admin.post('/users', body, headers={'Origin': 'https://evil.example'})
    assert foreign.status_code == 403 and foreign.json()['code'] == 'ORIGIN_FORBIDDEN'
    assert admin.post('/users', body, headers={'Origin': settings.admin_url}).status_code == 200


def test_roles_limit_what_staff_can_do(signed_in):
    viewer, content, catalog = signed_in('viewer'), signed_in('content'), signed_in('catalog')
    assert viewer.get('/products').status_code == 200
    assert viewer.put('/settings/index_threshold', {'value': 60}).status_code == 403
    assert content.get('/users').status_code == 403
    assert catalog.get('/subscribers').status_code == 403
    assert content.post('/redirects', {'source': '/old/', 'target': '/new/'}).status_code == 200
    assert catalog.post('/redirects', {'source': '/old2/', 'target': '/new/'}).status_code == 403


def test_totp_turns_on_and_is_asked_at_login(client, admin, sessions):
    setup = admin.ok(admin.post('/auth/totp/setup'))
    assert setup['uri'].startswith('otpauth://totp/')
    assert admin.post('/auth/totp/confirm', {'code': '000000'}).status_code == 422
    me = admin.ok(admin.post('/auth/totp/confirm', {'code': pyotp.TOTP(setup['secret']).now()}))
    assert me['totpEnabled'] is True
    first = client.post('/api/v1/admin/auth/login', json={'email': 'admin@ogk-chem.ru', 'password': PASSWORD})
    assert first.status_code == 401 and first.json()['code'] == 'TOTP_REQUIRED'
    with sessions() as db:
        assert db.scalar(select(StaffUser.totp_secret).where(StaffUser.email == 'admin@ogk-chem.ru')) != setup['secret']
    good = client.post('/api/v1/admin/auth/login', json={'email': 'admin@ogk-chem.ru', 'password': PASSWORD,
                                                        'code': pyotp.TOTP(setup['secret']).now()})
    assert good.status_code == 200


def test_administrators_must_turn_on_totp_outside_development(admin, monkeypatch):
    monkeypatch.setattr(settings, 'require_totp', True)
    blocked = admin.get('/products')
    assert blocked.status_code == 403 and blocked.json()['code'] == 'TOTP_SETUP_REQUIRED'
    assert admin.get('/auth/me').json()['totpSetupRequired'] is True


def test_staff_accounts_and_password_change(admin, signed_in, sessions):
    created = admin.ok(admin.post('/users', {'email': 'chemist@ogk-chem.ru', 'name': 'Химик', 'role': 'catalog',
                                              'password': 'long-enough-password'}))
    assert admin.post('/users', {'email': 'x@ogk-chem.ru', 'name': 'Икс', 'role': 'viewer',
                                 'password': 'short'}).json()['code'] == 'PASSWORD_WEAK'
    assert admin.patch(f'/users/{admin.me["id"]}', {'email': 'admin@ogk-chem.ru', 'name': 'Админ', 'role': 'viewer'}) \
        .json()['code'] == 'SELF_LOCKOUT'
    admin.ok(admin.patch(f'/users/{created["id"]}', {'email': 'chemist@ogk-chem.ru', 'name': 'Химик',
                                                     'role': 'catalog', 'active': False}))
    viewer = signed_in('viewer')
    assert viewer.post('/auth/password', {'current': 'wrong', 'password': 'new-long-password'}).status_code == 422
    assert viewer.ok(viewer.post('/auth/password', {'current': PASSWORD, 'password': 'new-long-password'}))
    with sessions() as db:
        user = db.scalar(select(StaffUser).where(StaffUser.email == 'viewer@ogk-chem.ru'))
        assert security.verify_password(user, 'new-long-password')
        actions = set(db.scalars(select(AuditEntry.action)))
    assert {'login', 'create', 'update', 'password_changed'} <= actions


def test_logout_closes_the_session(admin):
    assert admin.ok(admin.post('/auth/logout'))
    assert admin.get('/auth/me').status_code == 401
