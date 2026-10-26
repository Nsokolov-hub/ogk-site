"""Staff accounts of the admin panel from the command line: the first administrator, a lost password or phone.

    python -m app.admin.cli create-user --email it@ogk-chem.ru --name "Иван Петров" --role admin
    python -m app.admin.cli reset-password --email it@ogk-chem.ru
    python -m app.admin.cli reset-totp --email it@ogk-chem.ru
    python -m app.admin.cli users

A new password is generated and printed once; the staff member changes it in «Профиль».
"""

import argparse
import secrets
import string

from sqlalchemy import select, update

from app.admin import security
from app.admin.audit import record
from app.admin.models import ROLES, StaffSession, StaffUser
from app.core.db import SessionLocal


def new_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return '-'.join(''.join(secrets.choice(alphabet) for _ in range(5)) for _ in range(4))


def main() -> None:
    import app.models  # noqa: F401

    parser = argparse.ArgumentParser(description='Сотрудники админки')
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('create-user', help='новый сотрудник')
    command.add_argument('--email', required=True)
    command.add_argument('--name', required=True)
    command.add_argument('--role', choices=ROLES, default='admin')
    for name in ('reset-password', 'reset-totp'):
        command = commands.add_parser(name)
        command.add_argument('--email', required=True)
    commands.add_parser('users', help='список сотрудников')
    args = parser.parse_args()

    with SessionLocal.begin() as db:
        if args.command == 'users':
            for row in db.scalars(select(StaffUser).order_by(StaffUser.name)):
                state = 'активен' if row.active else 'отключён'
                print(f'{row.email:<35} {security.ROLE_NAMES[row.role]:<18} {state:<9} '
                      f'{"TOTP" if row.totp_enabled else "без TOTP"}')
            return
        email = args.email.strip().lower()
        user = db.scalar(select(StaffUser).where(StaffUser.email == email))
        if args.command == 'create-user':
            if user is not None:
                raise SystemExit('Сотрудник с этой почтой уже есть')
            password = new_password()
            user = StaffUser(email=email, name=args.name.strip(), role=args.role,
                             password_hash=security.hash_password(password))
            db.add(user)
            db.flush()
            record(db, None, 'staff', user.id, 'create', f'{user.name} (из командной строки)')
            print(f'Создан {email} ({security.ROLE_NAMES[args.role]}). Пароль: {password}')
            if args.role == 'admin':
                print('При первом входе админка попросит включить вход по коду из приложения (TOTP).')
            return
        if user is None:
            raise SystemExit('Сотрудник не найден')
        db.execute(update(StaffSession).where(StaffSession.user_id == user.id).values(revoked=True))
        if args.command == 'reset-password':
            password = new_password()
            user.password_hash, user.failed_logins, user.locked_until = security.hash_password(password), 0, None
            record(db, None, 'staff', user.id, 'password_reset', 'из командной строки')
            print(f'Новый пароль {email}: {password}')
        else:
            user.totp_secret, user.totp_enabled = None, False
            record(db, None, 'staff', user.id, 'totp_reset', 'из командной строки')
            print(f'Вход по коду для {email} выключен: при следующем входе его нужно включить снова.')


if __name__ == '__main__':
    main()
