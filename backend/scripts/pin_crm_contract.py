#!/usr/bin/env python3
"""Pin contract F1 from the CRM: copy the schemas of SiteRequestIn and SiteRequestReceipt with everything they
reference from the CRM's docs/openapi.json into backend/contracts/crm-f1.json.

    python3 backend/scripts/pin_crm_contract.py ../my-crm-project/docs/openapi.json
    python3 backend/scripts/pin_crm_contract.py ../my-crm-project/docs/openapi.json --check

The contract test (tests/test_contract.py) validates the body the site sends against this copy, so a change on
either side that breaks the contract fails CI. Re-pin after the CRM changes the contract on purpose.
"""

import argparse
import json
from pathlib import Path
from typing import Any

TARGET = Path(__file__).resolve().parents[1] / 'contracts' / 'crm-f1.json'
ROOTS = ('SiteRequestIn', 'SiteRequestReceipt')


def references(node: Any) -> set[str]:
    if isinstance(node, dict):
        found = {node['$ref'].split('/')[-1]} if isinstance(node.get('$ref'), str) else set()
        return found.union(*(references(value) for value in node.values()))
    if isinstance(node, list):
        return set().union(*(references(value) for value in node))
    return set()


def render(source: Path) -> str:
    schemas = json.loads(source.read_text(encoding='utf-8'))['components']['schemas']
    wanted, frontier = set(), set(ROOTS)
    while frontier:
        name = frontier.pop()
        wanted.add(name)
        frontier |= references(schemas[name]) - wanted
    document = {
        'description': 'Контракт F1 «заявка с сайта → CRM», закреплённый из docs/openapi.json Реактив CRM. '
                       'Не редактируйте вручную: python3 backend/scripts/pin_crm_contract.py <путь к openapi.json>.',
        'components': {'schemas': {name: schemas[name] for name in sorted(wanted)}},
    }
    return json.dumps(document, ensure_ascii=False, indent=2) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='Закрепить контракт F1 из CRM')
    parser.add_argument('openapi', type=Path, help='docs/openapi.json репозитория CRM')
    parser.add_argument('--check', action='store_true', help='проверить, что закреплённая копия актуальна')
    args = parser.parse_args()
    document = render(args.openapi)
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding='utf-8') != document:
            raise SystemExit('contracts/crm-f1.json расходится с CRM: перезакрепите контракт')
        print('Контракт F1 совпадает с CRM.')
        return
    TARGET.write_text(document, encoding='utf-8')
    print(f'Записано {TARGET}')


if __name__ == '__main__':
    main()
