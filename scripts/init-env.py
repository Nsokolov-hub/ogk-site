#!/usr/bin/env python3
"""First .env of a staging or production server with fresh random secrets (deploy/README.md).

    python3 scripts/init-env.py staging --domain staging.ogk-chem.ru --admin-domain admin-staging.ogk-chem.ru \
        --email it@ogk-chem.ru

Takes .env.example, fills the secrets and the server's names, prints the staging password once. An existing .env
is never overwritten. The staging password hash is made by Caddy itself (docker run caddy hash-password).
"""

import argparse
import re
import secrets
import shutil
import string
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CADDY_IMAGE = 'caddy:2.11.6-alpine'


def token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def password() -> str:
    alphabet = string.ascii_letters + string.digits
    return '-'.join(''.join(secrets.choice(alphabet) for _ in range(6)) for _ in range(3))


def caddy_hash(plain: str) -> str:
    if not shutil.which('docker'):
        sys.exit('Нужен Docker: хеш пароля стейджа делает Caddy')
    result = subprocess.run(['docker', 'run', '--rm', CADDY_IMAGE, 'caddy', 'hash-password', '--plaintext', plain],
                            check=True, capture_output=True, text=True)
    return result.stdout.strip()


def set_value(text: str, key: str, value: str) -> str:
    line = f'{key}={value}'
    pattern = re.compile(rf'^{re.escape(key)}=.*$', re.M)
    if pattern.search(text):
        return pattern.sub(lambda _: line, text, count=1)
    return text.rstrip('\n') + f'\n{line}\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='.env для стейджа или продакшена')
    parser.add_argument('environment', choices=['staging', 'production'])
    parser.add_argument('--domain', required=True, help='адрес сайта, например www.ogk-chem.ru')
    parser.add_argument('--admin-domain', required=True, help='адрес админки, например admin.ogk-chem.ru')
    parser.add_argument('--email', required=True, help='почта для сертификатов Let’s Encrypt')
    parser.add_argument('--aliases', default='', help='другие имена сайта для 301 на основной адрес')
    args = parser.parse_args()

    target = ROOT / '.env'
    if target.exists():
        sys.exit('.env уже есть — его не перезаписываю')
    text = (ROOT / '.env.example').read_text(encoding='utf-8')
    staging = args.environment == 'staging'
    values = {
        'ENVIRONMENT': args.environment,
        'SITE_ENV': args.environment,
        'SITE_DOMAIN': args.domain,
        'ADMIN_DOMAIN': args.admin_domain,
        'TLS_EMAIL': args.email,
        'SITE_ALIASES': args.aliases or ('' if staging else args.domain.removeprefix('www.')),
        'ADMIN_URL': f'https://{args.admin_domain}',
        'POSTGRES_PASSWORD': token(24),
        'MEILI_MASTER_KEY': token(32),
        'MEILI_ENV': 'production',
        'REVALIDATE_SECRET': token(32),
        'SECRET_KEY': token(48),
        'COMPOSE_PROFILES': 'mailpit' if staging else '',
    }
    plain = ''
    if staging:
        plain = password()
        values['STAGING_PASSWORD_HASH'] = f"'{caddy_hash(plain)}'"
    else:
        values.update({'SMTP_HOST': '', 'SMTP_PORT': '587', 'SMTP_STARTTLS': 'true'})
    for key, value in values.items():
        text = set_value(text, key, value)
    target.write_text(text, encoding='utf-8')
    target.chmod(0o600)
    print(f'Создан {target}. Заполните CRM_*, SMTP_* и TELEGRAM_* (deploy/README.md).')
    if plain:
        print(f'Пароль стейджа — пользователь ogk, пароль {plain}. Сохраните его: в .env только хеш.')


if __name__ == '__main__':
    main()
