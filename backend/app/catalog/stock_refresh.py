"""Frequent stock verification, separate from the long catalogue-discovery crawl.

Chimmed's known manufacturers are rechecked through its public warehouse feed, including explicit delayed
rows. Dia-m's already matched, published offers are revisited directly. The pass never creates products or
reconciles an entire supplier as empty: missing/uncertain rows expire under the short evidence lifetime, while
explicit negative evidence is applied atomically with each page. Its durable queue survives worker restarts.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.catalog import competitors
from app.catalog.models import CompetitorOffer, Packaging, Product
from app.catalog.settings import get_setting, set_setting
from app.catalog.stock_availability import public_products
from app.catalog.stock_sources.base import Page, ParseChanged, PublicClient, Refused
from app.core.config import settings
from app.core.db import as_utc, utcnow
from app.core.logs import event

logger = logging.getLogger(__name__)
SUPPORTED = {'chimmed', 'diam'}
RUN_KEY = 'competitor_refresh_run'
RESULT_KEY = 'competitor_refresh_results'


def configured(db: Session) -> list[str]:
    sources = (get_setting(db, 'competitor_stock') or {}).get('sources') or []
    return list(dict.fromkeys(source for source in sources if source in SUPPORTED))


def due(db: Session, now: datetime | None = None) -> bool:
    """Every two hours from the previous pass's start, independently of discovery completion."""
    if not competitors.enabled():
        return False
    if get_setting(db, RUN_KEY):
        return True
    if not configured(db):
        return False
    config = get_setting(db, 'competitor_stock') or {}
    interval = timedelta(hours=float(config.get('refresh_hours') or 2))
    result = get_setting(db, RESULT_KEY) or {}
    stamp = result.get('startedAt') or result.get('finishedAt')
    return not stamp or (now or utcnow()) - as_utc(datetime.fromisoformat(stamp)) >= interval


def start(db: Session, now: datetime) -> dict[str, Any]:
    sources = configured(db)
    tasks: list[dict[str, Any]] = []
    if 'chimmed' in sources:
        tasks.append({'s': 'chimmed', 'k': 'refresh-start'})
    if 'diam' in sources:
        # Include expired observations too: a current positive page can restore legitimately renewed stock.
        # Only already matched, public products enter this verification lane; discovery owns other products.
        offers = db.scalars(select(CompetitorOffer).join(Packaging, and_(
            Packaging.id == CompetitorOffer.packaging_id, Packaging.product_id == CompetitorOffer.product_id))
            .join(Product, Product.id == CompetitorOffer.product_id).where(
            CompetitorOffer.source == 'diam', public_products(db))
            .order_by(CompetitorOffer.url, CompetitorOffer.external_id))
        urls: dict[str, list[str]] = {}
        for offer in offers:
            urls.setdefault(offer.url, []).append(offer.external_id)
        tasks.extend({'s': 'diam', 'url': url, 'page': 1, 'expected_ids': sorted(set(ids))}
                     for url, ids in urls.items())
    return {'startedAt': now.isoformat(), 'queue': tasks,
            'scheduled': {source: [json.dumps(task, sort_keys=True) for task in tasks if task['s'] == source]
                          for source in sources},
            'stats': {source: {'pages': 0, 'offers': 0, 'matched': 0, 'withdrawn': 0, 'errors': 0,
                               'truncated': 0, 'refused': None, 'incomplete': None} for source in sources}}


def fetch(client: PublicClient, task: dict[str, Any], brands: competitors.Brands) -> Page:
    source = task['s']
    if source == 'chimmed' and task.get('k') == 'refresh-start':
        response = client.get(f'{competitors.CHIMMED}/products/storage')
        makers = [name for name in dict.fromkeys(competitors.chimmed_manufacturers(response.text))
                  if brands.find(name) is not None]
        return Page(tasks=[{'s': 'chimmed', 'k': 'list', 'm': name, 'letter': '', 'page': 1} for name in makers])
    # PublicClient deliberately implements the small get/post contract used by these adapters.
    page = competitors.SOURCES[source](client, task, lambda name: brands.find(name) is not None)  # type: ignore[arg-type]
    if source == 'diam':
        # A direct detail check must not turn into a second general catalogue crawler. Incomplete/ambiguous
        # pages do not renew missing offers; their old evidence expires instead of being assumed negative.
        page.tasks = []
    return page


def turn(sessions: sessionmaker[Session], seconds: float = competitors.TURN_SECONDS) -> dict[str, Any] | None:
    with sessions.begin() as db:
        competitors.settle(db, utcnow(), [], utcnow())
        if not due(db):
            return None
        run = get_setting(db, RUN_KEY) or start(db, utcnow())
        set_setting(db, RUN_KEY, run)
        config = get_setting(db, 'competitor_stock') or {}
        pause_seconds = float(config.get('pause_seconds') or 2)
        batch_limit = max(1, int(config.get('max_pages_per_source') or 120))
        brands = competitors.Brands(db)
    deadline = time.monotonic() + seconds
    first = True
    counts: dict[str, int] = {}
    with competitors.http_client() as client:
        clients: dict[str, PublicClient] = {}
        while run['queue'] and time.monotonic() < deadline:
            task = competitors._next_task(run, counts, batch_limit)
            if task is None:
                break
            source, stats = task['s'], run['stats'][task['s']]
            if stats['refused']:
                continue
            if not first:
                competitors.pause(pause_seconds)
            first = False
            try:
                if source not in clients:
                    meta = competitors.META[source]
                    clients[source] = PublicClient(client, str(meta['origin']), settings.competitor_user_agent,
                                                   list(meta['paths']))
                    competitors.pause(pause_seconds)
                page = fetch(clients[source], task, brands)
                if any(next_task.get('s') != source for next_task in page.tasks):
                    raise ParseChanged('cross-source refresh task')
            except Refused as exc:
                reason = str(exc)
                if source in clients and reason in ('robots_disallow', 'path_not_allowed', 'redirect_loop',
                                                    'redirect_limit', 'redirect_requires_review', 'origin_not_allowed'):
                    stats['incomplete'] = reason
                    stats['refused'] = reason if not any(t['s'] == source for t in run['queue']) else None
                else:
                    stats['refused'] = reason
                    run['queue'] = [pending for pending in run['queue'] if pending['s'] != source]
                event(logger, 'stock_refresh_refused', logging.WARNING, source=source, answer=reason)
            except ParseChanged as exc:
                stats['incomplete'] = str(exc)[:200]
                event(logger, 'stock_refresh_parser_changed', logging.WARNING, source=source, error=str(exc)[:200])
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                if task.get('tries', 0) + 1 < competitors.ATTEMPTS:
                    run['queue'].append({**task, 'tries': task.get('tries', 0) + 1})
                else:
                    stats['errors'] += 1
                event(logger, 'stock_refresh_page_failed', logging.WARNING, source=source, error=str(exc)[:200])
            else:
                with sessions.begin() as db:
                    withdrawn = db.scalar(select(func.count()).select_from(CompetitorOffer).where(
                        CompetitorOffer.source == source,
                        CompetitorOffer.external_id.in_(set(page.unavailable_ids)))) if page.unavailable_ids else 0
                    kept, hits = competitors.save_page(db, source, page, brands, utcnow())
                    competitors._enqueue(run, source, page.tasks)
                    stats['pages'] += 1
                    stats['offers'] += kept
                    stats['matched'] += hits
                    stats['withdrawn'] += int(withdrawn or 0)
                    stats['truncated'] += page.truncated
                    if page.incomplete:
                        stats['incomplete'] = page.incomplete
                    set_setting(db, RUN_KEY, run)
                continue
            with sessions.begin() as db:
                set_setting(db, RUN_KEY, run)
    if run['queue']:
        return run
    with sessions.begin() as db:
        now = utcnow()
        # This pass intentionally covers known brands/direct matched URLs, never all rows of a supplier.
        competitors.settle(db, now, [], datetime.fromisoformat(run['startedAt']))
        result = {'startedAt': run['startedAt'], 'finishedAt': now.isoformat(), 'scope': 'known_stock',
                  'sources': {source: {**stats, 'complete': not any((stats['refused'], stats['errors'],
                              stats['truncated'], stats.get('incomplete')))} for source, stats in run['stats'].items()}}
        set_setting(db, RESULT_KEY, result)
        set_setting(db, RUN_KEY, None)
    event(logger, 'stock_refreshed', **{source: stats['matched'] for source, stats in run['stats'].items()})
    return result
