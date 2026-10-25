"""Sign-in, profile and staff accounts (ADM-01)."""

from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.admin import security
from app.admin.audit import record
from app.admin.models import ROLES, StaffSession, StaffUser
from app.admin.security import StaffDep, requires
from app.core.db import DB
from app.core.errors import DomainError
from app.core.ratelimit import RateLimiter

router = APIRouter()
login_limiter = RateLimiter('admin-login')


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    code: str | None = Field(default=None, max_length=10)


@router.post('/auth/login')
async def login(body: LoginIn, request: Request, response: Response, db: DB) -> dict[str, Any]:
    ip = request.client.host if request.client else None
    if not login_limiter.allow(ip or 'unknown', 20):
        raise DomainError('RATE_LIMITED', 'Слишком много попыток входа. Повторите через минуту', 429)
    try:
        user, session, token = await run_in_threadpool(security.login, db, body.email, body.password, body.code, ip,
                                                       request.headers.get('user-agent'))
    except DomainError:
        # Wrong attempts are counted even though the request fails: they lock the account (ADM-01).
        db.commit()
        raise
    security.set_cookie(response, token, int((session.expires_at - session.created_at).total_seconds()))
    record(db, user, 'staff', user.id, 'login', f'вход с {ip or "—"}')
    return security.me(user, session)


@router.post('/auth/logout')
def logout(staff: StaffDep, response: Response, db: DB) -> dict[str, bool]:
    staff.session.revoked = True
    security.clear_cookie(response)
    return {'ok': True}


@router.get('/auth/me')
def me(staff: StaffDep) -> dict[str, Any]:
    return security.me(staff.user, staff.session)


@router.post('/auth/totp/setup')
def totp_setup(staff: StaffDep, db: DB) -> dict[str, str]:
    """Новый секрет TOTP: показать QR-код или ключ, затем подтвердить кодом из приложения."""
    secret, uri = security.new_totp(staff.user)
    db.flush()
    return {'secret': secret, 'uri': uri}


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=10)


@router.post('/auth/totp/confirm')
def totp_confirm(body: CodeIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    if not security.totp_valid(staff.user, body.code):
        raise DomainError('TOTP_INVALID', 'Код не подошёл: проверьте время на телефоне', 422, 'code')
    staff.user.totp_enabled = True
    record(db, staff, 'staff', staff.id, 'totp_enabled', 'включён вход по коду')
    return security.me(staff.user, staff.session)


class PasswordIn(BaseModel):
    current: str = Field(max_length=200)
    password: str = Field(max_length=200)


@router.post('/auth/password')
def change_password(body: PasswordIn, staff: StaffDep, db: DB) -> dict[str, bool]:
    if not security.verify_password(staff.user, body.current):
        raise DomainError('PASSWORD_WRONG', 'Текущий пароль неверный', 422, 'current')
    security.check_password_strength(body.password)
    staff.user.password_hash = security.hash_password(body.password)
    db.execute(update(StaffSession).where(StaffSession.user_id == staff.id, StaffSession.id != staff.session.id)
               .values(revoked=True))
    record(db, staff, 'staff', staff.id, 'password_changed', 'пароль изменён, другие сеансы закрыты')
    return {'ok': True}


def user_out(user: StaffUser) -> dict[str, Any]:
    return {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role,
            'roleName': security.ROLE_NAMES[user.role], 'active': user.active, 'totpEnabled': user.totp_enabled,
            'lastLoginAt': user.last_login_at.isoformat() if user.last_login_at else None}


@router.get('/users', dependencies=[requires('users.write')])
def users(db: DB) -> dict[str, Any]:
    rows = db.scalars(select(StaffUser).order_by(StaffUser.name))
    return {'items': [user_out(u) for u in rows],
            'roles': [{'key': r, 'name': security.ROLE_NAMES[r], 'permissions': security.permissions(r)} for r in ROLES]}


class UserIn(BaseModel):
    email: str = Field(max_length=254)
    name: str = Field(min_length=2, max_length=200)
    role: str
    password: str | None = Field(default=None, max_length=200)
    active: bool = True


@router.post('/users', dependencies=[requires('users.write')])
def create_user(body: UserIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    email = body.email.strip().lower()
    if body.role not in ROLES:
        raise DomainError('ROLE_INVALID', 'Нет такой роли', 422, 'role')
    if db.scalar(select(StaffUser.id).where(StaffUser.email == email)):
        raise DomainError('EMAIL_TAKEN', 'Сотрудник с этой почтой уже есть', 409, 'email')
    security.check_password_strength(body.password or '')
    user = StaffUser(email=email, name=body.name.strip(), role=body.role,
                     password_hash=security.hash_password(body.password or ''), active=body.active)
    db.add(user)
    db.flush()
    record(db, staff, 'staff', user.id, 'create', f'{user.name} ({security.ROLE_NAMES[user.role]})')
    return user_out(user)


@router.patch('/users/{user_id}', dependencies=[requires('users.write')])
def update_user(user_id: str, body: UserIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    user = db.get(StaffUser, user_id)
    if user is None:
        raise DomainError('NOT_FOUND', 'Сотрудник не найден', 404)
    if body.role not in ROLES:
        raise DomainError('ROLE_INVALID', 'Нет такой роли', 422, 'role')
    if user.id == staff.id and (body.role != 'admin' or not body.active):
        raise DomainError('SELF_LOCKOUT', 'Нельзя снять права администратора с самого себя', 422, 'role')
    before = user_out(user)
    user.name, user.role, user.active = body.name.strip(), body.role, body.active
    if body.password:
        security.check_password_strength(body.password)
        user.password_hash = security.hash_password(body.password)
    if not user.active or body.password:
        db.execute(update(StaffSession).where(StaffSession.user_id == user.id).values(revoked=True))
    record(db, staff, 'staff', user.id, 'update', user.name, before, user_out(user))
    return user_out(user)


@router.post('/users/{user_id}/reset-totp', dependencies=[requires('users.write')])
def reset_totp(user_id: str, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Сотрудник потерял телефон: вход по коду выключается, при следующем входе его нужно включить снова."""
    user = db.get(StaffUser, user_id)
    if user is None:
        raise DomainError('NOT_FOUND', 'Сотрудник не найден', 404)
    user.totp_secret, user.totp_enabled = None, False
    db.execute(update(StaffSession).where(StaffSession.user_id == user.id).values(revoked=True))
    record(db, staff, 'staff', user.id, 'totp_reset', user.name)
    return user_out(user)
