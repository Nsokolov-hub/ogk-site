"""Actual confirmed money is distinct from a commercial stage, append-only and counted once."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.crm.funnel import report
from app.crm.payments import for_requests
from app.requests.models import SiteRequest, SiteRequestPayment
from tests.test_crm_events import (
    VISITOR,
    events_on,  # noqa: F401
    outbox,
    send,
    site_request,
)


def received(client, identifier, payment_id='p-1', amount='500', currency='RUB', **extra):
    return send(client, 'request.payment_received', {
        'site_request_id': identifier, 'crm_request_id': 'crm-deal-1', 'crm_request_number': '196',
        'payment': {'id': payment_id, 'amount': amount, 'currency': currency,
                    'confirmed_at': '2026-11-15T10:00:00Z'}, **extra})


def refunded(client, identifier, refund_id='refund-1', payment_id='p-1', amount='100', currency='RUB'):
    return send(client, 'request.payment_refunded', {
        'site_request_id': identifier, 'crm_request_id': 'crm-deal-1',
        'refund': {'id': refund_id, 'payment_id': payment_id, 'amount': amount, 'currency': currency,
                   'refunded_at': '2026-11-15T12:00:00Z'}})


def test_confirmed_partial_receipt_does_not_claim_a_sale_and_is_idempotent(client, sessions):
    identifier = site_request(client, cookies=VISITOR)
    first = received(client, identifier)
    assert first.status_code == 200, first.text
    assert first.json()['conversions'] == 2
    repeat = received(client, identifier)
    assert repeat.status_code == 200 and repeat.json()['duplicate'] is True
    with sessions() as db:
        [entry] = list(db.scalars(select(SiteRequestPayment)))
        row = db.get(SiteRequest, identifier)
        assert row is not None
        assert entry.amount == Decimal('500') and entry.kind == 'received'
        assert row.crm_stage is None and row.sale_amount is None
        assert row.crm_request_id == 'crm-deal-1'
        assert for_requests(db, [identifier])[identifier][0]['net'] == '500.00000000'
    queued = outbox(sessions, 'conversion.')
    assert len(queued) == 2
    assert all('value' not in event.payload and 'currency' not in event.payload for event in queued)
    assert received(client, identifier, amount='501').status_code == 409
    # A second real receipt changes the ledger but cannot create a second first-payment goal.
    second = received(client, identifier, payment_id='p-2', amount='250')
    assert second.status_code == 200 and second.json()['conversions'] == 0
    with sessions() as db:
        assert Decimal(for_requests(db, [identifier])[identifier][0]['net']) == 750


def test_refund_before_receipt_is_pending_then_reconciles_and_currencies_stay_separate(client, sessions):
    identifier = site_request(client)
    assert refunded(client, identifier, amount='20').status_code == 200
    with sessions() as db:
        [rub] = for_requests(db, [identifier])[identifier]
        assert Decimal(rub['net']) == 0 and Decimal(rub['pendingRefunds']) == 20
    assert received(client, identifier, amount='100', currency='RUR').status_code == 200
    assert refunded(client, identifier, amount='20').json()['duplicate'] is True
    assert received(client, identifier, payment_id='usd-payment', amount='5', currency='USD').status_code == 200
    with sessions() as db:
        money = {row['currency']: row for row in for_requests(db, [identifier])[identifier]}
        assert Decimal(money['RUB']['received']) == 100
        assert Decimal(money['RUB']['refunded']) == 20
        assert Decimal(money['RUB']['net']) == 80 and Decimal(money['RUB']['pendingRefunds']) == 0
        assert Decimal(money['USD']['net']) == 5
        totals = report(db, 30)['totals']
        assert totals['paymentReceived'] == 1
        assert len(totals['payments']) == 2  # No invented RUB+USD grand total.
    assert len(outbox(sessions, 'conversion.')) == 0  # Money is kept even without analytics identifiers.


def test_refund_cannot_change_payment_owner_currency_or_exceed_the_receipt(client):
    identifier, other = site_request(client), site_request(client)
    assert received(client, identifier, amount='100').status_code == 200
    assert refunded(client, other).status_code == 409
    assert refunded(client, identifier, currency='USD').status_code == 409
    assert refunded(client, identifier, amount='100.01').status_code == 422
    assert refunded(client, identifier, amount='100').status_code == 200
    assert refunded(client, identifier, refund_id='over-refund', amount='1').status_code == 422


@pytest.mark.parametrize('change', [
    {'amount': '0'}, {'amount': '-1'}, {'amount': 'NaN'}, {'amount': 'Infinity'},
    {'amount': '1.000000001'}, {'currency': 'RRRR'}, {'confirmed_at': 'not a date'},
    {'confirmed_at': '2026-11-15T10:00:00'}, {'id': ''},
])
def test_payment_facts_are_validated(client, change):
    identifier = site_request(client)
    payload = {'id': str(uuid4()), 'amount': '100', 'currency': 'RUB',
               'confirmed_at': '2026-11-15T10:00:00Z', **change}
    response = send(client, 'request.payment_received', {'site_request_id': identifier, 'payment': payload})
    assert response.status_code == 422, response.text


def test_payment_ledger_cannot_be_edited_or_deleted(client, sessions):
    identifier = site_request(client)
    assert received(client, identifier).status_code == 200
    with pytest.raises(IntegrityError), sessions.begin() as db:
        row = db.scalar(select(SiteRequestPayment))
        assert row is not None
        row.amount = Decimal('999')
    with pytest.raises(IntegrityError), sessions.begin() as db:
        db.execute(delete(SiteRequestPayment))
    with sessions() as db:
        assert db.scalar(select(SiteRequestPayment.amount)) == Decimal('500')


def test_funnel_keeps_reached_milestones_after_loss_and_counts_merged_deals_once(client, sessions):
    first, second = site_request(client), site_request(client)
    base = {'site_request_id': first, 'crm_request_id': 'same-crm-deal', 'stage': 'proposal_sent'}
    assert send(client, 'request.stage_changed', base).status_code == 200
    assert send(client, 'request.closed', {**base, 'lost': True}).status_code == 200
    assert send(client, 'request.stage_changed', {**base, 'site_request_id': second,
                                                 'stage': 'sale_confirmed'}).status_code == 200
    with sessions() as db:
        lost = db.get(SiteRequest, first)
        assert lost is not None
        assert lost.crm_stage == 'lost' and lost.qualified_at and lost.proposal_sent_at
        assert lost.order_confirmed_at is None
        totals = report(db, 30)['totals']
        assert totals['leads'] == 2 and totals['deals'] == 1
        assert totals['qualified'] == totals['proposals'] == totals['confirmedOrders'] == 1
        assert totals['paymentReceived'] == 0


def test_legacy_stage_evidence_does_not_fabricate_dates_or_payment(client, sessions):
    identifier = site_request(client)
    with sessions.begin() as db:
        row = db.get(SiteRequest, identifier)
        assert row is not None
        row.crm_stage = 'proposal_sent'
        row.crm_status = 'converted'
    with sessions() as db:
        data = report(db, 30)
        assert data['historyIncomplete'] == 1
        assert data['totals']['qualified'] == data['totals']['proposals'] == 1
        assert data['totals']['confirmedOrders'] == data['totals']['paymentReceived'] == 0
        row = db.get(SiteRequest, identifier)
        assert row is not None
        assert row.qualified_at is None and row.proposal_sent_at is None and row.order_confirmed_at is None
