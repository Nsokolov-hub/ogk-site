"""Offline conversions (flow F3): what became of a site request in the CRM goes to Yandex Metrica and GA4.

The site knows the visitor (the ClientID cookies of both counters and yclid, kept with the request's attribution);
the CRM knows what happened next and reports it with events (app.crm.events). Three goals, each sent once per
request: ``qualified`` — the CRM started collecting quotes, ``proposal`` — a proposal went to the customer,
``sale`` — a confirmed sale, with its revenue. Only the identifiers of the counters leave the site, never contacts.

Metrica: goals «JavaScript-событие» with the identifiers of METRIKA_TARGETS and offline conversions turned on in the
counter's settings; the upload needs METRIKA_OAUTH_TOKEN. GA4: events of GA_EVENTS through the Measurement Protocol
with GA_API_SECRET. Without the token or the secret that system is skipped.
"""

from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.settings import get_setting
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import DomainError
from app.outbox.models import OutboxEvent
from app.requests.models import SiteRequest

METRIKA_URL = 'https://api-metrika.yandex.net/management/v1/counter/{counter}/offline_conversions/upload'
GA_URL = 'https://www.google-analytics.com/mp/collect'
METRIKA_TARGETS = {'qualified': 'crm_qualified', 'proposal': 'crm_proposal', 'sale': 'crm_sale'}
# qualify_lead and close_convert_lead are GA4's recommended lead events; the proposal has no standard name.
GA_EVENTS = {'qualified': 'qualify_lead', 'proposal': 'crm_proposal', 'sale': 'close_convert_lead'}
# The answer will not change on a repeat: the upload itself is wrong (a person must look).
PERMANENT = {400, 404, 413, 415, 422}


def counters(db: Session) -> tuple[str, str]:
    """(Metrica counter, GA4 measurement id): the admin panel's numbers, else the server's."""
    values = get_setting(db, 'counters') or {}
    return (str(values.get('ym') or settings.ym_counter_id or ''),
            str(values.get('ga') or settings.ga_measurement_id or ''))


def identities(row: SiteRequest) -> dict[str, str | None]:
    attribution = row.attribution or {}
    client_ids = attribution.get('client_ids') or {}
    touches = [attribution.get('last_touch') or {}, attribution.get('first_touch') or {}]
    return {'ym_uid': client_ids.get('ym_uid') or None, 'ga_client_id': client_ids.get('ga_client_id') or None,
            'yclid': next((t['yclid'] for t in touches if t.get('yclid')), None)}


def queue(db: Session, row: SiteRequest, goal: str) -> int:
    """The goal for each counter that can recognise the visitor; a goal already queued is not queued again."""
    ym, ga = counters(db)
    ids = identities(row)
    systems = []
    if ym and settings.metrika_oauth_token and (ids['ym_uid'] or ids['yclid']):
        systems.append('metrika')
    if ga and settings.ga_api_secret and ids['ga_client_id']:
        systems.append('ga4')
    payload: dict[str, Any] = {'request_id': row.id, 'goal': goal, 'at': utcnow().isoformat()}
    if goal == 'sale' and row.sale_amount is not None:
        payload.update(value=str(row.sale_amount), currency=row.sale_currency or 'RUB')
    queued = 0
    for system in systems:
        key = f'conversion-{system}:{row.id}:{goal}'
        if db.scalar(select(OutboxEvent.id).where(OutboxEvent.event_key == key)) is None:
            db.add(OutboxEvent(event_key=key, kind=f'conversion.{system}', payload=payload))
            queued += 1
    return queued


def http_client() -> httpx.Client:
    """Replaced in tests with a client on a mock transport."""
    return httpx.Client(timeout=15)


def post(system: str, url: str, **kwargs: Any) -> None:
    try:
        with http_client() as client:
            response = client.post(url, **kwargs)
    except httpx.HTTPError:
        raise DomainError(f'{system}_UNREACHABLE', 'Сервис аналитики не отвечает', 503) from None
    if response.status_code >= 300:
        status = 400 if response.status_code in PERMANENT else 503
        raise DomainError(f'{system}_HTTP_{response.status_code}', response.text[:200], status)


def send(db: Session, kind: str, payload: dict[str, Any]) -> None:
    row = db.get(SiteRequest, payload.get('request_id'))
    goal = str(payload.get('goal'))
    if row is None or goal not in METRIKA_TARGETS:
        return
    ym, ga = counters(db)
    ids = identities(row)
    if kind == 'conversion.metrika':
        if not (ym and settings.metrika_oauth_token):
            return
        if ids['ym_uid']:
            id_type, column, value = 'CLIENT_ID', 'ClientId', ids['ym_uid']
        elif ids['yclid']:
            id_type, column, value = 'YCLID', 'Yclid', ids['yclid']
        else:
            return
        at = int(datetime.fromisoformat(str(payload['at'])).timestamp())
        header, line = [column, 'Target', 'DateTime'], [value, METRIKA_TARGETS[goal], str(at)]
        if payload.get('value'):
            header += ['Price', 'Currency']
            line += [str(payload['value']), str(payload.get('currency') or 'RUB')]
        body = (','.join(header) + '\n' + ','.join(line) + '\n').encode()
        post('METRIKA', METRIKA_URL.format(counter=ym), params={'client_id_type': id_type},
             headers={'Authorization': f'OAuth {settings.metrika_oauth_token}'},
             files={'file': ('conversions.csv', body, 'text/csv')})
    elif kind == 'conversion.ga4':
        if not (ga and settings.ga_api_secret and ids['ga_client_id']):
            return
        params: dict[str, Any] = {'crm_goal': goal}
        if payload.get('value'):
            params.update(value=float(payload['value']), currency=str(payload.get('currency') or 'RUB'),
                          transaction_id=row.number)
        post('GA4', GA_URL, params={'measurement_id': ga, 'api_secret': settings.ga_api_secret},
             json={'client_id': ids['ga_client_id'], 'events': [{'name': GA_EVENTS[goal], 'params': params}]})
