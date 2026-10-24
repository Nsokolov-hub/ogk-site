"""The body the site sends satisfies contract F1 as the CRM publishes it (contracts/crm-f1.json)."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.crm.client import payload
from app.requests.models import SiteRequest
from tests.support import PDF, form, submit

CONTRACT = json.loads((Path(__file__).resolve().parents[1] / 'contracts' / 'crm-f1.json').read_text())


def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator({'$ref': f'#/components/schemas/{name}', **CONTRACT})


@pytest.mark.parametrize('body', [
    form(),
    form(kind='one_click', formType='one_click', desiredDate=None),
    form(kind='general', items=[], customer={**form()['customer'], 'inn': None, 'city': None}),
    form(kind='service', items=[], service={'slug': 'cold-chain', 'name': 'Холодовая цепь',
                                            'fields': {'Откуда': 'Германия'}}),
    form(lang='en', items=[{'name': 'Free line: column C18 250×4.6', 'quantity': 3, 'unit': 'pack',
                            'analogue': 'requested', 'customPackaging': True, 'packaging': '50 mg'}]),
])
def test_sent_body_matches_the_crm_contract(client, sessions, body):
    request_id = submit(client, body, attachment=('spec.pdf', PDF, 'application/pdf')).json()['siteRequestId']
    with sessions() as db:
        sent, files = payload(db, db.get(SiteRequest, request_id))
    errors = sorted(validator('SiteRequestIn').iter_errors(json.loads(json.dumps(sent))), key=str)
    assert not errors, [error.message for error in errors]
    assert len(files) == len(sent['attachments']) == 1


def test_receipt_shape_is_known():
    receipt = {'id': 'x', 'number': 'W-1', 'status': 'new', 'received_at': '2026-10-24T10:00:00Z'}
    assert not list(validator('SiteRequestReceipt').iter_errors(receipt))
