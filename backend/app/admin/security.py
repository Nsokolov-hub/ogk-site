"""Sign-in of the admin panel (ADM-01): passwords, a second factor, server sessions, CSRF and roles.

A session is a random token in an httpOnly cookie limited to /api/v1/admin; its hash is kept in the database.
Every change also needs the session's CSRF token in X-CSRF-Token and comes only from ADMIN_URL. Ten wrong
passwords lock the account for 15 minutes. Administrators must turn on TOTP before they can work (outside
development).
"""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Any

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.models import StaffSession, StaffUser
from app.core.config import settings
from app.core.db import DB, as_utc, utcnow
from app.core.errors import DomainError

COOKIE = 'ogk_admin'
COOKIE_PATH = '/api/v1/admin'
LOCK_AFTER = 10
LOCK_FOR = timedelta(minutes=15)
IDLE = timedelta(hours=2)
hasher = PasswordHasher()

ROLE_NAMES = {'admin': 'Администратор', 'content': 'Контент и SEO', 'catalog': 'Каталог-менеджер',
              'viewer': 'Просмотр'}
# Rights of each role; the administrator has all of them. Personal data of customers (requests, subscribers)
# is seen by administrators only (ADM-08).
GRANTS: dict[str, set[str]] = {
    'content': {'dashboard', 'pages.read', 'pages.write', 'taxonomy.read', 'taxonomy.write', 'seo.read', 'seo.write',
                'products.read', 'queues.read', 'requests.journal', 'settings.read', 'forms.write', 'feeds.read',
                'import.read', 'dictionaries.read', 'audit.read'},
    'catalog': {'dashboard', 'pages.read', 'taxonomy.read', 'taxonomy.write', 'seo.read', 'products.read',
                'products.write', 'import.read', 'import.write', 'queues.read', 'queues.write', 'dictionaries.read',
                'dictionaries.write', 'feeds.read', 'feeds.write', 'requests.journal', 'settings.read', 'audit.read'},
    'viewer': {'dashboard', 'pages.read', 'taxonomy.read', 'seo.read', 'products.read', 'queues.read',
               'requests.journal', 'settings.read', 'feeds.read', 'import.read', 'dictionaries.read', 'audit.read'},
}


def can(role: str, permission: str) -> bool:
    return role == 'admin' or permission in GRANTS.get(role, set())


def permissions(role: str) -> list[str]:
    if role == 'admin':
        every = set().union(*GRANTS.values()) | {'users.write', 'settings.write', 'requests.pii', 'requests.resend',
                                                 'subscribers.read', 'audit.rollback'}
        return sorted(every)
    return sorted(GRANTS.get(role, set()))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def cipher() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(f'totp:{settings.secret_key}'.encode()).digest()))


def hash_password(password: str) -> str:
    return hasher.hash(password)


def check_password_strength(password: str) -> None:
    if len(password) < 12:
        raise DomainError('PASSWORD_WEAK', 'Пароль — не короче 12 символов', 422, 'password')


def verify_password(user: StaffUser, password: str) -> bool:
    try:
        return hasher.verify(user.password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def totp_secret(user: StaffUser) -> str | None:
    if not user.totp_secret:
        return None
    try:
        return cipher().decrypt(user.totp_secret.encode()).decode()
    except InvalidToken:
        return None


def totp_valid(user: StaffUser, code: str) -> bool:
    secret = totp_secret(user)
    return bool(secret) and pyotp.TOTP(secret).verify(code.replace(' ', ''), valid_window=1)  # type: ignore[arg-type]


def new_totp(user: StaffUser) -> tuple[str, str]:
    secret = pyotp.random_base32()
    user.totp_secret = cipher().encrypt(secret.encode()).decode()
    user.totp_enabled = False
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name='ОГК-ХИМ админка')
    return secret, uri


def needs_totp_setup(user: StaffUser) -> bool:
    return settings.totp_required and user.role == 'admin' and not user.totp_enabled


def login(db: Session, email: str, password: str, code: str | None, ip: str | None,
          user_agent: str | None) -> tuple[StaffUser, StaffSession, str]:
    user = db.scalar(select(StaffUser).where(StaffUser.email == email.strip().lower()).with_for_update())
    now = utcnow()
    if user is not None and user.locked_until and as_utc(user.locked_until) > now:
        raise DomainError('ACCOUNT_LOCKED', 'Слишком много неверных попыток. Повторите через 15 минут', 429)
    if user is None or not user.active or not verify_password(user, password):
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= LOCK_AFTER:
                user.locked_until, user.failed_logins = now + LOCK_FOR, 0
            db.flush()
        raise DomainError('LOGIN_FAILED', 'Неверная почта или пароль', 401)
    if user.totp_enabled:
        if not code:
            raise DomainError('TOTP_REQUIRED', 'Введите код из приложения-аутентификатора', 401, 'code')
        if not totp_valid(user, code):
            user.failed_logins += 1
            db.flush()
            raise DomainError('TOTP_INVALID', 'Код не подошёл: проверьте время на телефоне', 401, 'code')
    user.failed_logins, user.locked_until, user.last_login_at = 0, None, now
    token = secrets.token_urlsafe(32)
    session = StaffSession(user_id=user.id, token_hash=digest(token), csrf_token=secrets.token_urlsafe(32),
                           expires_at=now + timedelta(hours=settings.admin_session_hours), last_seen_at=now,
                           ip=ip, user_agent=(user_agent or '')[:300] or None)
    db.add(session)
    db.flush()
    return user, session, token


def set_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(COOKIE, token, max_age=max_age, path=COOKIE_PATH, httponly=True, samesite='strict',
                        secure=settings.environment != 'development')


def clear_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path=COOKIE_PATH)


@dataclass
class Staff:
    user: StaffUser
    session: StaffSession

    @property
    def id(self) -> str:
        return self.user.id

    @property
    def name(self) -> str:
        return self.user.name

    def can(self, permission: str) -> bool:
        return can(self.user.role, permission)

    def require(self, permission: str) -> None:
        if not self.can(permission):
            raise DomainError('FORBIDDEN', 'Недостаточно прав для этого действия', 403)


def allowed_origin(origin: str | None) -> bool:
    return origin is None or origin.rstrip('/') == settings.admin_url.rstrip('/')


def current_staff(request: Request, db: DB) -> Staff:
    token = request.cookies.get(COOKIE)
    if not token:
        raise DomainError('UNAUTHENTICATED', 'Войдите в админку', 401)
    session = db.scalar(select(StaffSession).where(StaffSession.token_hash == digest(token),
                                                   StaffSession.revoked.is_(False)))
    now = utcnow()
    if session is None or as_utc(session.expires_at) <= now or now - as_utc(session.last_seen_at) > IDLE:
        raise DomainError('SESSION_EXPIRED', 'Сеанс завершён. Войдите снова', 401)
    user = db.get(StaffUser, session.user_id)
    if user is None or not user.active:
        raise DomainError('SESSION_REVOKED', 'Доступ к админке отозван', 401)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if not hmac.compare_digest(session.csrf_token, request.headers.get('x-csrf-token', '')):
            raise DomainError('CSRF_INVALID', 'Обновите страницу и повторите действие', 403)
        if not allowed_origin(request.headers.get('origin')):
            raise DomainError('ORIGIN_FORBIDDEN', 'Источник запроса не разрешён', 403)
    if now - as_utc(session.last_seen_at) > timedelta(minutes=1):
        session.last_seen_at = now
    if needs_totp_setup(user) and not request.url.path.startswith('/api/v1/admin/auth/'):
        raise DomainError('TOTP_SETUP_REQUIRED', 'Включите вход по коду из приложения: раздел «Профиль»', 403)
    return Staff(user, session)


StaffDep = Annotated[Staff, Depends(current_staff)]


def requires(permission: str) -> Any:
    """Route dependency: the signed-in staff member with this right."""

    def check(staff: StaffDep) -> Staff:
        staff.require(permission)
        return staff

    return Depends(check)


def me(user: StaffUser, session: StaffSession) -> dict[str, Any]:
    return {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role,
            'roleName': ROLE_NAMES[user.role], 'permissions': permissions(user.role),
            'totpEnabled': user.totp_enabled, 'totpSetupRequired': needs_totp_setup(user),
            'csrfToken': session.csrf_token}
