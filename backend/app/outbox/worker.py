"""Transactional outbox worker. Run: python -m app.outbox.worker (see backend/README.md).

Besides the outbox it keeps the search index in step with the catalog: products marked ``needs_index`` are
pushed to the engine every iteration, so a change is searchable within a minute (TZ 6).

Retries of the CRM delivery follow RFQ-07: 1, 5, 15 and 60 minutes, then hourly for 24 hours. A request the
CRM has not taken within 15 minutes raises an alert in Telegram (without personal data) and by e-mail (with
the full content, so a manager can process it by hand). Rows are taken FOR UPDATE SKIP LOCKED, so several
worker processes never handle one event twice.
"""

import argparse
import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.catalog.search import indexer
from app.catalog.search.engine import EngineUnavailable
from app.catalog.search.meili import engine as search_engine
from app.core import storefront
from app.core.config import settings
from app.core.db import SessionLocal, as_utc, utcnow
from app.core.errors import DomainError
from app.core.logs import configure_logging, event
from app.core.monitoring import Watchdog, init_sentry
from app.crm import client as crm
from app.notifications import mail, telegram, texts
from app.outbox.models import OutboxEvent
from app.requests import antispam
from app.requests.models import DeliveryAttempt, SiteRequest
from app.subscriptions.models import Subscriber

logger = logging.getLogger('site.worker')
CRM_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15), timedelta(minutes=60))
CRM_WINDOW = timedelta(hours=24)
MAIL_ATTEMPTS = 12
BATCH = 25


@dataclass
class Result:
    kind: Literal['succeeded', 'retry', 'failed']
    error: str | None = None


def crm_delay(attempt: int) -> timedelta:
    return CRM_DELAYS[min(attempt, len(CRM_DELAYS)) - 1]


def mail_delay(attempt: int) -> timedelta:
    return min(timedelta(hours=1), timedelta(seconds=30) * 2 ** (attempt - 1))


def queue_alert(db: Session, row: SiteRequest, reason: str, key: str, attempts: int = 0) -> None:
    event_key = f'alert:{row.id}:{key}'
    if db.scalar(select(OutboxEvent.id).where(OutboxEvent.event_key == event_key)) is None:
        db.add(OutboxEvent(event_key=event_key, kind='alert',
                           payload={'request_id': row.id, 'reason': reason, 'attempts': attempts}))
        db.flush()


def request_of(db: Session, outbox: OutboxEvent) -> SiteRequest:
    row = db.scalar(select(SiteRequest).where(SiteRequest.id == outbox.payload.get('request_id')).with_for_update()
                    .execution_options(populate_existing=True))
    if row is None:
        raise DomainError('REQUEST_NOT_FOUND', 'Заявка задания не найдена', 404)
    return row


def deliver(db: Session, outbox: OutboxEvent) -> Result:
    row = request_of(db, outbox)
    if row.status == 'delivered':
        return Result('succeeded')
    started = time.monotonic()
    outcome = crm.deliver(db, row)
    db.add(DeliveryAttempt(request_id=row.id, attempt=outbox.attempts, outcome=outcome.kind,
                           status_code=outcome.status_code, error_code=outcome.error_code,
                           duration_ms=round((time.monotonic() - started) * 1000)))
    event(logger, 'crm_delivery', number=row.number, attempt=outbox.attempts, outcome=outcome.kind,
          status=outcome.status_code, error=outcome.error_code)
    if outcome.kind == 'delivered':
        row.status = 'delivered'
        row.crm_id = outcome.crm_id
        row.crm_number = outcome.crm_number or None
        row.delivered_at = utcnow()
        row.delivery_error = None
        row.version += 1
        return Result('succeeded')
    row.delivery_error = outcome.error_code
    row.version += 1
    if outcome.alert_now:
        queue_alert(db, row, 'CRM отклонила заявку' if outcome.kind == 'failed' else 'CRM не принимает вызовы сайта',
                    f'now:{outcome.error_code}', outbox.attempts)
    if outcome.kind == 'failed':
        row.status = 'failed'
        return Result('failed', outcome.error_code)
    return Result('retry', outcome.error_code)


def send_customer(db: Session, outbox: OutboxEvent) -> Result:
    row = request_of(db, outbox)
    subject, body = texts.customer_letter(db, row)
    mail.send([row.email], subject, body, reply_to=settings.mail_reply_to)
    return Result('succeeded')


def send_sales(db: Session, outbox: OutboxEvent) -> Result:
    row = request_of(db, outbox)
    subject, body = texts.sales_letter(db, row)
    mail.send([settings.sales_email], subject, body, reply_to=row.email)
    return Result('succeeded')


def send_alert(db: Session, outbox: OutboxEvent) -> Result:
    row = request_of(db, outbox)
    reason = str(outbox.payload.get('reason') or 'не доставлена')
    if outbox.attempts == 1:
        telegram.send(texts.alert_message(row, reason, int(outbox.payload.get('attempts') or 0)))
    subject, body = texts.alert_letter(db, row, reason)
    mail.send(settings.alert_emails.split(','), subject, body)
    return Result('succeeded')


def delete_from_index(db: Session, outbox: OutboxEvent) -> Result:
    """Products removed from the catalog (a rolled-back import) leave the search index."""
    search_engine().delete(settings.meili_index, [str(i) for i in outbox.payload.get('ids') or []])
    return Result('succeeded')


def subscriber_of(db: Session, outbox: OutboxEvent) -> Subscriber:
    row = db.get(Subscriber, outbox.payload.get('subscriber_id'))
    if row is None:
        raise DomainError('SUBSCRIBER_NOT_FOUND', 'Подписчик не найден', 404)
    return row


def send_subscriber(db: Session, outbox: OutboxEvent) -> Result:
    row = subscriber_of(db, outbox)
    if row.status != 'active':
        return Result('succeeded')
    subject, body = texts.subscriber_letter(row)
    # One-click unsubscribe for mail clients (RFC 8058) next to the link in the text.
    mail.send([row.email], subject, body, reply_to=settings.mail_reply_to,
              headers={'List-Unsubscribe': f'<{texts.unsubscribe_url(row)}>'})
    return Result('succeeded')


def send_subscriber_sales(db: Session, outbox: OutboxEvent) -> Result:
    subject, body = texts.subscriber_sales_letter(subscriber_of(db, outbox))
    mail.send([settings.sales_email], subject, body)
    return Result('succeeded')


def deliver_subscriber(db: Session, outbox: OutboxEvent) -> Result:
    """The subscriber as a contact for mailings in the CRM; the latest state wins (one key per version)."""
    from app.subscriptions.service import crm_payload

    row = subscriber_of(db, outbox)
    outcome = crm.post_json(crm.SUBSCRIBERS_PATH, crm_payload(row), f'{row.id}:{row.version}')
    if outcome.kind == 'delivered':
        row.crm_synced_at = utcnow()
        return Result('succeeded')
    return Result('failed' if outcome.kind == 'failed' else 'retry', outcome.error_code)


HANDLERS = {'crm.deliver': deliver, 'mail.customer': send_customer, 'mail.sales': send_sales, 'alert': send_alert,
            'search.delete': delete_from_index, 'mail.subscriber': send_subscriber,
            'mail.subscriber_sales': send_subscriber_sales, 'crm.subscriber': deliver_subscriber}


def dispatch(db: Session, outbox: OutboxEvent) -> Result:
    handler = HANDLERS.get(outbox.kind)
    if handler is None:
        return Result('failed', 'OUTBOX_KIND_UNKNOWN')
    try:
        # Unexpected failures roll back the handler's writes; the attempt and its error stay recorded.
        with db.begin_nested():
            result = handler(db, outbox)
            db.flush()
        return result
    except mail.MailUnavailable:
        return Result('retry', 'MAIL_UNAVAILABLE')
    except EngineUnavailable:
        return Result('retry', 'SEARCH_UNAVAILABLE')
    except DomainError as exc:
        return Result('failed' if exc.status in (400, 404, 422) else 'retry', exc.code)
    except Exception:
        logger.exception('{"event": "outbox_handler_failed"}')
        return Result('retry', 'HANDLER_FAILED')


def finish_failed_delivery(db: Session, outbox: OutboxEvent, reason: str) -> None:
    row = db.get(SiteRequest, outbox.payload.get('request_id'))
    if row is not None and row.status != 'delivered':
        row.status = 'failed'
        row.version += 1
        queue_alert(db, row, reason, 'final', outbox.attempts)


def process_events(db: Session, now: datetime | None = None, limit: int = BATCH) -> dict[str, int]:
    """Handle a bounded batch within the caller's transaction; the caller commits."""
    now = now or utcnow()
    counts = {'succeeded': 0, 'retried': 0, 'failed': 0}
    statement = select(OutboxEvent).where(OutboxEvent.status == 'pending', or_(
        OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now))
    if not settings.crm_delivery_enabled:
        # Requests and subscribers wait in the queue, sales get them by e-mail meanwhile.
        statement = statement.where(OutboxEvent.kind.not_like('crm.%'))
    events = db.scalars(statement.order_by(OutboxEvent.created_at, OutboxEvent.id).limit(limit)
                        .with_for_update(skip_locked=True)).all()
    for outbox in events:
        outbox.attempts += 1
        outbox.started_at = now
        outbox.version += 1
        result = dispatch(db, outbox)
        outbox.error = result.error
        if result.kind == 'succeeded':
            outbox.status, outbox.finished_at, outbox.next_attempt_at = 'succeeded', now, None
            counts['succeeded'] += 1
            continue
        final = result.kind == 'failed'
        if result.kind == 'retry' and outbox.kind == 'crm.deliver':
            window_start = as_utc(datetime.fromisoformat(outbox.payload.get('window_start') or now.isoformat()))
            if now - window_start >= CRM_WINDOW:
                final = True
                finish_failed_delivery(db, outbox, 'не доставлена за 24 часа')
            else:
                outbox.next_attempt_at = now + crm_delay(outbox.attempts)
        elif result.kind == 'retry' and outbox.kind == 'search.delete':
            # The index can be rebuilt from PostgreSQL at any time; keep trying, but not too often.
            outbox.next_attempt_at = now + mail_delay(min(outbox.attempts, 8))
        elif result.kind == 'retry':
            if outbox.attempts >= MAIL_ATTEMPTS:
                final = True
            else:
                outbox.next_attempt_at = now + mail_delay(outbox.attempts)
        if final:
            outbox.status, outbox.finished_at, outbox.next_attempt_at = 'failed', now, None
            counts['failed'] += 1
            event(logger, 'outbox_failed', logging.WARNING, kind=outbox.kind, attempts=outbox.attempts,
                  error=outbox.error)
        else:
            outbox.status = 'pending'
            counts['retried'] += 1
    db.flush()
    return counts


def watch_undelivered(db: Session, now: datetime | None = None) -> int:
    """Alert once about every request the CRM has not taken within ALERT_AFTER_MINUTES."""
    if not settings.crm_delivery_enabled:
        return 0
    now = now or utcnow()
    late = db.scalars(select(SiteRequest).where(
        SiteRequest.status == 'accepted', SiteRequest.alerted_at.is_(None),
        SiteRequest.created_at <= now - timedelta(minutes=settings.alert_after_minutes),
    ).with_for_update(skip_locked=True)).all()
    for row in late:
        row.alerted_at = now
        row.version += 1
        queue_alert(db, row, f'не доставлена за {settings.alert_after_minutes} минут', 'late')
    return len(late)


def index_catalog(limit: int = 5) -> int:
    """Up to ``limit`` batches of queued products; the engine being down leaves them queued."""
    total = 0
    for _ in range(limit):
        changed: list[str] = []
        try:
            with SessionLocal.begin() as db:
                done = indexer.index_pending(db, search_engine(), changed=changed)
        except EngineUnavailable as exc:
            event(logger, 'search_index_unavailable', logging.WARNING, error=str(exc)[:200])
            break
        total += done
        if changed:
            revalidate_pages(changed)
        if not done:
            break
    return total


def revalidate_pages(slugs: list[str]) -> None:
    """Drop the storefront's cached data of changed products; a mass import leaves pages to their cache time."""
    if len(slugs) < storefront.MAX_TAGS:
        storefront.revalidate(['catalog', *(f'product:{slug}' for slug in slugs)])


def sync_brands_if_due() -> None:
    """The nightly load of the CRM manufacturer registry (flow F5); failures wait for the next day's try."""
    from app.catalog import brands_sync

    if not (settings.crm_delivery_enabled and brands_sync.configured()):
        return
    with SessionLocal() as db:
        if not brands_sync.due(db):
            return
    try:
        brands_sync.sync(SessionLocal)
    except brands_sync.SyncFailed as exc:
        event(logger, 'brands_sync_failed', logging.WARNING, error=str(exc)[:300])
        with SessionLocal.begin() as db:
            from app.catalog.settings import set_setting

            # Try again in an hour, not every minute.
            set_setting(db, 'brands_sync_run_at', (utcnow() - timedelta(hours=23)).isoformat())


_index_ready = False


def ensure_search_index() -> None:
    """Once per worker start, retried while the engine is down."""
    global _index_ready
    if _index_ready:
        return
    try:
        with SessionLocal() as db:
            if indexer.ensure_index(db, search_engine()):
                event(logger, 'search_index_created', index=settings.meili_index)
        _index_ready = True
    except EngineUnavailable as exc:
        event(logger, 'search_index_unavailable', logging.WARNING, error=str(exc)[:200])


def run_once(*, housekeeping: bool = True) -> dict[str, int]:
    ensure_search_index()
    if housekeeping:
        with SessionLocal.begin() as db:
            watch_undelivered(db)
            antispam.prune(db)
            prune_carts(db)
        sync_brands_if_due()
    with SessionLocal.begin() as db:
        counts = process_events(db)
    counts['indexed'] = index_catalog()
    return counts


def prune_carts(db: Session, now: datetime | None = None) -> int:
    """Guest carts live 90 days after the last change (RFQ-01)."""
    from sqlalchemy import delete

    from app.catalog.models import Cart

    result = db.execute(delete(Cart).where(Cart.updated_at < (now or utcnow()) - timedelta(days=90)))
    return int(getattr(result, 'rowcount', 0) or 0)


def main() -> None:
    import app.models  # noqa: F401  (all tables known before the first query)

    parser = argparse.ArgumentParser(description='Очередь заявок сайта: доставка в CRM, письма, алерты')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=float, default=2.0)
    args = parser.parse_args()
    configure_logging()
    init_sentry('worker')
    watchdog = Watchdog()
    running = True

    def stop(signum: int, _frame: object) -> None:
        nonlocal running
        event(logger, 'worker_stopping', signal=signum)
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    event(logger, 'worker_started', crm_delivery=settings.crm_delivery_enabled)
    last_housekeeping = 0.0
    while running:
        try:
            housekeeping = time.monotonic() - last_housekeeping >= 60
            counts = run_once(housekeeping=housekeeping)
            if housekeeping:
                last_housekeeping = time.monotonic()
            if any(counts.values()):
                event(logger, 'outbox_batch', **counts)
            if watchdog.due():
                with SessionLocal() as db:
                    watchdog.run(db, telegram.send)
        except Exception:
            logger.exception('{"event": "worker_iteration_failed"}')
            if args.once:
                raise
        if args.once:
            break
        deadline = time.monotonic() + max(0.2, min(args.interval, 30))
        while running and time.monotonic() < deadline:
            time.sleep(0.1)
    event(logger, 'worker_stopped')


if __name__ == '__main__':
    main()
