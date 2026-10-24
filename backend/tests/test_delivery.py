"""The worker delivers requests to the CRM (flow F1), retries on schedule and raises alerts (RFQ-07)."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from email.parser import BytesParser
from email.policy import default

import httpx
import pytest
from sqlalchemy import select

from app.cli import resend
from app.core.config import settings
from app.core.db import as_utc, utcnow
from app.crm import client as crm
from app.notifications import mail, texts
from app.outbox import worker
from app.outbox.models import OutboxEvent
from app.requests.models import DeliveryAttempt, SiteRequest
from tests.support import PDF, form, submit


class FakeCRM:
    """Answers like the CRM endpoint and keeps what it received."""

    def __init__(self, *answers: httpx.Response | Exception):
        self.answers = list(answers)
        self.calls: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def fake_crm(monkeypatch):
    def install(*answers: httpx.Response | Exception) -> FakeCRM:
        fake = FakeCRM(*answers)
        monkeypatch.setattr(crm, 'http_client', lambda: httpx.Client(transport=httpx.MockTransport(fake.handle)))
        return fake
    return install


def accepted(number: str = 'W-1') -> httpx.Response:
    return httpx.Response(201, json={'id': 'crm-uuid-1', 'number': number, 'status': 'new',
                                     'received_at': '2026-10-24T10:00:00Z'})


def failure(status: int, code: str) -> httpx.Response:
    return httpx.Response(status, json={'code': code, 'message': '…', 'field': None, 'requestId': 'r'})


def run(sessions, now: datetime | None = None) -> dict[str, int]:
    with sessions.begin() as db:
        return worker.process_events(db, now=now)


def delivery_event(sessions, request_id: str) -> OutboxEvent:
    with sessions() as db:
        return db.scalar(select(OutboxEvent).where(OutboxEvent.event_key == f'crm-deliver:{request_id}'))


def multipart(request: httpx.Request) -> tuple[dict, list[tuple[str | None, object]]]:
    head = f'Content-Type: {request.headers["Content-Type"]}\r\n\r\n'.encode()
    message = BytesParser(policy=default).parsebytes(head + request.content)
    payload: dict = {}
    files: list[tuple[str | None, object]] = []
    for part in message.iter_parts():
        name = part.get_param('name', header='content-disposition')
        if name == 'payload':
            payload = json.loads(part.get_content())
        else:
            files.append((part.get_filename(), part.get_payload(decode=True)))
    return payload, files


def test_request_is_delivered_signed_and_journaled(client, sessions, fake_crm):
    crm_side = fake_crm(accepted())
    request_id = submit(client, form(), attachment=('spec.pdf', PDF, 'application/pdf')).json()['siteRequestId']
    assert run(sessions)['succeeded'] == 3
    call = crm_side.calls[0]
    assert str(call.url) == 'https://crm.test/api/v1/integrations/site/requests'
    assert call.headers['Authorization'] == 'Bearer ogk_site_test-token'
    assert call.headers['Idempotency-Key'] == request_id
    stamp = call.headers['X-Site-Timestamp']
    expected = hmac.new(b'test-signing-secret', stamp.encode() + b'.' + call.content, hashlib.sha256).hexdigest()
    assert call.headers['X-Site-Signature'] == f'sha256={expected}'
    payload, files = multipart(call)
    assert payload['site_request_id'] == request_id and payload['customer']['inn'] == '7707083893'
    assert payload['attachments'] == [{'file_name': 'spec.pdf', 'sha256': hashlib.sha256(PDF).hexdigest(),
                                       'size': len(PDF)}]
    assert files == [('spec.pdf', PDF)]
    with sessions() as db:
        row = db.get(SiteRequest, request_id)
        assert (row.status, row.crm_number, row.crm_id) == ('delivered', 'W-1', 'crm-uuid-1')
        attempt = db.scalar(select(DeliveryAttempt).where(DeliveryAttempt.request_id == request_id))
        assert (attempt.outcome, attempt.status_code) == ('delivered', 201)


def test_unavailable_crm_is_retried_on_schedule(client, sessions, fake_crm):
    fake_crm(failure(503, 'TRANSACTION_RETRY'))
    request_id = submit(client, form()).json()['siteRequestId']
    now = utcnow()
    for delay in (1, 5, 15, 60, 60):
        run(sessions, now)
        event = delivery_event(sessions, request_id)
        assert event.status == 'pending' and event.error == 'TRANSACTION_RETRY'
        assert event.next_attempt_at is not None
        assert as_utc(event.next_attempt_at) == now + timedelta(minutes=delay)
        now = as_utc(event.next_attempt_at)
    with sessions() as db:
        assert db.get(SiteRequest, request_id).status == 'accepted'


def test_timeout_is_retried(client, sessions, fake_crm):
    fake_crm(httpx.ReadTimeout('slow'))
    request_id = submit(client, form()).json()['siteRequestId']
    run(sessions)
    assert delivery_event(sessions, request_id).error == 'CRM_TIMEOUT'


def test_repeat_after_a_lost_answer_is_accepted_as_delivered(client, sessions, fake_crm):
    fake_crm(httpx.ReadTimeout('lost'), httpx.Response(200, json={'id': 'crm-uuid-1', 'number': 'W-1',
                                                                    'status': 'new', 'received_at': 'x'}))
    request_id = submit(client, form()).json()['siteRequestId']
    run(sessions)
    run(sessions, utcnow() + timedelta(minutes=2))
    with sessions() as db:
        assert db.get(SiteRequest, request_id).status == 'delivered'


def test_refused_request_fails_at_once_with_an_alert(client, sessions, fake_crm):
    fake_crm(failure(422, 'VALIDATION_ERROR'))
    request_id = submit(client, form()).json()['siteRequestId']
    run(sessions)
    with sessions() as db:
        row = db.get(SiteRequest, request_id)
        assert (row.status, row.delivery_error) == ('failed', 'VALIDATION_ERROR')
        assert delivery_event(sessions, request_id).status == 'failed'
        alert = db.scalar(select(OutboxEvent).where(OutboxEvent.kind == 'alert'))
        assert alert.event_key == f'alert:{request_id}:now:VALIDATION_ERROR'
    assert run(sessions)['succeeded'] == 1


def test_configuration_errors_alert_once_and_keep_retrying(client, sessions, fake_crm):
    fake_crm(failure(401, 'INTEGRATION_SIGNATURE_INVALID'))
    request_id = submit(client, form()).json()['siteRequestId']
    run(sessions)
    run(sessions, utcnow() + timedelta(minutes=2))
    with sessions() as db:
        assert db.get(SiteRequest, request_id).status == 'accepted'
        assert len(db.scalars(select(OutboxEvent).where(OutboxEvent.kind == 'alert')).all()) == 1
    assert delivery_event(sessions, request_id).status == 'pending'


def test_delivery_gives_up_after_24_hours(client, sessions, fake_crm):
    fake_crm(failure(503, 'TRANSACTION_RETRY'))
    request_id = submit(client, form()).json()['siteRequestId']
    run(sessions, utcnow() + timedelta(hours=24, minutes=1))
    with sessions() as db:
        assert db.get(SiteRequest, request_id).status == 'failed'
        assert db.scalar(select(OutboxEvent).where(OutboxEvent.event_key == f'alert:{request_id}:final'))
    assert delivery_event(sessions, request_id).status == 'failed'


def test_late_request_raises_one_alert(client, sessions, fake_crm):
    fake_crm(failure(503, 'TRANSACTION_RETRY'))
    submit(client, form())
    later = utcnow() + timedelta(minutes=16)
    with sessions.begin() as db:
        assert worker.watch_undelivered(db, later) == 1
    with sessions.begin() as db:
        assert worker.watch_undelivered(db, later + timedelta(minutes=30)) == 0


def test_with_delivery_off_requests_wait_and_sales_get_letters(client, sessions, fake_crm, monkeypatch):
    crm_side = fake_crm(accepted())
    monkeypatch.setattr(settings, 'crm_delivery_enabled', False)
    request_id = submit(client, form()).json()['siteRequestId']
    assert run(sessions)['succeeded'] == 2
    assert not crm_side.calls
    with sessions.begin() as db:
        assert worker.watch_undelivered(db, utcnow() + timedelta(hours=1)) == 0
    assert delivery_event(sessions, request_id).status == 'pending'
    monkeypatch.setattr(settings, 'crm_delivery_enabled', True)
    run(sessions)
    with sessions() as db:
        assert db.get(SiteRequest, request_id).status == 'delivered'


def test_mail_server_outage_is_retried(client, sessions, fake_crm, monkeypatch):
    fake_crm(accepted())

    def unavailable(*_args, **_kwargs):
        raise mail.MailUnavailable('SMTPServerDisconnected')

    monkeypatch.setattr(mail, 'send', unavailable)
    submit(client, form())
    counts = run(sessions)
    assert counts == {'succeeded': 1, 'retried': 2, 'failed': 0}


def test_failed_request_can_be_resent(client, sessions, fake_crm):
    fake_crm(failure(422, 'VALIDATION_ERROR'), accepted())
    request_id = submit(client, form()).json()['siteRequestId']
    run(sessions)
    with sessions.begin() as db:
        resend(db, db.get(SiteRequest, request_id).number)
    run(sessions)
    with sessions() as db:
        assert db.get(SiteRequest, request_id).status == 'delivered'


def test_telegram_alert_carries_no_personal_data(client, sessions):
    request_id = submit(client, form()).json()['siteRequestId']
    with sessions() as db:
        row = db.get(SiteRequest, request_id)
        message = texts.alert_message(row, 'не доставлена за 15 минут', 4)
        assert row.number in message
        assert not any(value in message for value in (row.company, row.customer_name, row.phone, row.email))


def test_customer_letter_uses_the_language_of_the_request(client, sessions):
    request_id = submit(client, form(lang='en')).json()['siteRequestId']
    with sessions() as db:
        subject, body = texts.customer_letter(db, db.get(SiteRequest, request_id))
        assert subject.startswith('Your request S-') and 'within 2 business hours' in body
