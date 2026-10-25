#!/usr/bin/env python3
"""Write the OpenAPI document of the site API to backend/openapi.json; --check fails if it is stale.

The storefront generates its TypeScript types from this file (npm run api:types), so the two stay in step.
"""

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TARGET = BACKEND / 'openapi.json'


def render() -> str:
    # Building the schema needs no database: the engine is created lazily and never connects.
    os.environ.setdefault('DATABASE_URL', 'sqlite://')
    sys.path.insert(0, str(BACKEND))
    from app.main import app

    return json.dumps(app.openapi(), ensure_ascii=False, indent=2) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='Выгрузить OpenAPI API сайта в backend/openapi.json')
    parser.add_argument('--check', action='store_true', help='не записывать, а проверить актуальность файла')
    args = parser.parse_args()
    document = render()
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding='utf-8') != document:
            raise SystemExit('backend/openapi.json устарел: выполните python3 backend/scripts/export_openapi.py')
        print('backend/openapi.json актуален.')
        return
    TARGET.write_text(document, encoding='utf-8')
    print(f'Записано {TARGET.relative_to(BACKEND.parent)}.')


if __name__ == '__main__':
    main()
