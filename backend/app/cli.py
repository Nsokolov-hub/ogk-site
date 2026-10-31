"""Operations on requests until the admin panel has its journal (ADM-08).

    python -m app.cli status                 — counts by status and the queue
    python -m app.cli undelivered            — requests not yet in the CRM
    python -m app.cli resend S-123   — deliver a failed request again (a new 24-hour window)
    python -m app.cli subscribers [--all] > subscribers.csv — subscribers of the mailing for a mailing service
"""

import argparse
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, as_utc, utcnow
from app.outbox.models import OutboxEvent
from app.requests.models import SiteRequest


def status(db: Session) -> list[str]:
    lines = [f'{state:<10} {count}' for state, count in
             db.execute(select(SiteRequest.status, func.count()).group_by(SiteRequest.status))]
    lines += [f'в очереди {kind:<14} {count}' for kind, count in
              db.execute(select(OutboxEvent.kind, func.count()).where(OutboxEvent.status == 'pending')
                         .group_by(OutboxEvent.kind))]
    return lines


def undelivered(db: Session) -> list[str]:
    now = utcnow()
    rows = db.scalars(select(SiteRequest).where(SiteRequest.status != 'delivered')
                      .order_by(SiteRequest.created_at)).all()
    lines = []
    for row in rows:
        age = now - as_utc(row.created_at)
        age -= timedelta(microseconds=age.microseconds)
        lines.append(f'{row.number}  {row.status:<9} {age!s:>16}  {row.delivery_error or "—"}')
    return lines or ['Все заявки доставлены в CRM.']


def resend(db: Session, number: str) -> str:
    row = db.scalar(select(SiteRequest).where(SiteRequest.number == number))
    if row is None:
        raise SystemExit('Заявка не найдена')
    if row.status == 'delivered':
        raise SystemExit(f'Заявка уже в CRM: {row.crm_number}')
    outbox = db.scalar(select(OutboxEvent).where(OutboxEvent.event_key == f'crm-deliver:{row.id}'))
    if outbox is None:
        outbox = OutboxEvent(event_key=f'crm-deliver:{row.id}', kind='crm.deliver', payload={})
        db.add(outbox)
    outbox.payload = {'request_id': row.id, 'window_start': utcnow().isoformat()}
    outbox.status, outbox.attempts, outbox.next_attempt_at, outbox.error = 'pending', 0, None, None
    row.status, row.delivery_error, row.alerted_at = 'accepted', None, None
    row.version += 1
    db.flush()
    return f'Заявка {row.number} поставлена в очередь доставки.'


def main() -> None:
    import app.models  # noqa: F401

    parser = argparse.ArgumentParser(description='Заявки сайта')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status', help='сводка')
    commands.add_parser('undelivered', help='недоставленные в CRM')
    command = commands.add_parser('resend', help='отправить в CRM повторно')
    command.add_argument('number')
    command = commands.add_parser('subscribers', help='подписчики рассылки в CSV')
    command.add_argument('--all', action='store_true', help='и отписавшиеся')
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        if args.command == 'subscribers':
            from app.subscriptions.service import export_csv

            print(export_csv(db, None if args.all else 'active'), end='')
        elif args.command == 'status':
            print('\n'.join(status(db)))
        elif args.command == 'undelivered':
            print('\n'.join(undelivered(db)))
        else:
            print(resend(db, args.number))


if __name__ == '__main__':
    main()
