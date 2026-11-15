"""Lead cohorts, distinct CRM deals and actual receipts, with missing historical evidence made explicit."""

from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import utcnow
from app.crm.payments import totals as payment_totals
from app.requests.models import SiteRequest, SiteRequestPayment

CHANNEL_NAMES = {'cpc': 'Реклама', 'organic': 'Поиск', 'referral': 'Переходы с сайтов', 'direct': 'Прямые заходы',
                 'email': 'Рассылки', 'social': 'Соцсети', 'unknown': 'Не определён'}
STAGES = ('new', 'clarification', 'collecting_quotes', 'quote_given', 'calculation', 'proposal_sent',
          'composition_agreed', 'awaiting_payment', 'sale_confirmed')
COUNTS = ('leads', 'deals', 'qualified', 'proposals', 'confirmedOrders', 'paymentReceived')


def report(db: Session, period: int) -> dict[str, Any]:
    zone = ZoneInfo(settings.company_timezone)
    end = datetime.now(zone).date()
    start = end - timedelta(days=period - 1)
    rows = list(db.scalars(select(SiteRequest).where(
        SiteRequest.created_at >= datetime.combine(start, time.min, zone),
        SiteRequest.created_at < datetime.combine(end + timedelta(days=1), time.min, zone)
    ).order_by(SiteRequest.created_at, SiteRequest.id)))
    identifiers = [row.id for row in rows]
    entries = list(db.scalars(select(SiteRequestPayment).where(SiteRequestPayment.site_request_id.in_(identifiers)))) if identifiers else []
    received = {entry.site_request_id for entry in entries if entry.kind == 'received'}
    table: dict[str, dict[str, Any]] = {}
    deals: dict[str, dict[str, Any]] = {}
    lead_channels: dict[str, str] = {}
    incomplete = 0
    for row in rows:
        channel = (row.attribution or {}).get('channel') or 'unknown'
        if channel not in CHANNEL_NAMES:
            channel = 'unknown'
        lead_channels[row.id] = channel
        line = table.setdefault(channel, {'channel': channel, 'name': CHANNEL_NAMES[channel],
                                          **dict.fromkeys(COUNTS, 0)})
        line['leads'] += 1
        stage_name = row.crm_stage or ''
        stage = STAGES.index(stage_name) if stage_name in STAGES else -1
        flags = {'qualified': row.qualified_at is not None or stage >= STAGES.index('collecting_quotes'),
                 'proposals': row.proposal_sent_at is not None or stage >= STAGES.index('proposal_sent'),
                 'confirmedOrders': row.order_confirmed_at is not None or row.crm_stage == 'sale_confirmed',
                 'paymentReceived': row.id in received}
        if ((row.crm_status == 'converted' and not row.crm_request_id) or
            (row.crm_stage and row.crm_stage not in ('new', 'clarification') and
            ((flags['qualified'] and row.qualified_at is None) or
             (flags['proposals'] and row.proposal_sent_at is None) or
             (flags['confirmedOrders'] and row.order_confirmed_at is None) or
             (row.crm_stage == 'lost' and not (row.qualified_at or row.proposal_sent_at or row.order_confirmed_at))))):
            incomplete += 1
        # The first site request in the cohort owns the channel of the deal; four forms merged into one deal
        # remain four source leads but cannot become four orders or four paid customers.
        key = row.crm_request_id or f'site:{row.id}'
        deal = deals.setdefault(key, {'channel': channel, 'known': bool(row.crm_request_id),
                                      **dict.fromkeys(flags, False)})
        deal['known'] |= bool(row.crm_request_id)
        for flag, value in flags.items():
            deal[flag] |= value
    for deal in deals.values():
        line = table[deal['channel']]
        line['deals'] += deal['known']
        for key in COUNTS[2:]:
            line[key] += deal[key]
    for channel, line in table.items():
        line['payments'] = payment_totals([entry for entry in entries if lead_channels[entry.site_request_id] == channel])
    channels = [table[channel] for channel in CHANNEL_NAMES if channel in table]
    return {'dateFrom': start.isoformat(), 'dateTo': end.isoformat(), 'asOf': utcnow().isoformat(),
            'historyIncomplete': incomplete,
            'channels': channels, 'totals': {**{key: sum(line[key] for line in channels) for key in COUNTS},
                                           'payments': payment_totals(entries)}}
