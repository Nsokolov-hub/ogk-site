"""IndexNow (03.11.2026): search engines learn about a new or changed page at once, not on their next crawl.

Anything that changes a public page queues its path (the admin panel's publications, the nightly build of the CAS
pages, `cli index-pilot`); the worker sends the queue to Yandex at most every SEND_EVERY, up to BATCH addresses at
a time, and only in production. The key is public by design: the storefront serves it as /<key>.txt
(public/<key>.txt), and Yandex checks that file before it takes the addresses.

    python -m app.catalog.cli indexnow-sitemap   — queue every Russian address of the Sitemap (after a launch)
"""

import logging
import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any
from xml.etree import ElementTree

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import IndexNowUrl
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.core.db import utcnow
from app.core.logs import event

logger = logging.getLogger(__name__)

ENDPOINT = 'https://yandex.com/indexnow'
BATCH = 10_000
SEND_EVERY = timedelta(minutes=10)
CHUNK = 1000
# Russian pages only: English ones follow through hreflang and the Sitemap.
SKIP = re.compile(r'^/(?:en|admin|api|internal|search|rfq|account|unsubscribe)(?:/|$)')


def enabled() -> bool:
    return settings.environment == 'production' and bool(settings.indexnow_key)


def normalize(path: str) -> str | None:
    """A path of the site as the queue keeps it: with the leading slash, without the host; None for what is not a
    public Russian page."""
    value = path.strip()
    if value.startswith(settings.site_url):
        value = value[len(settings.site_url):]
    if not value.startswith('/') or SKIP.match(value) or len(value) > 500:
        return None
    return value


def queue(db: Session, paths: Iterable[str]) -> int:
    """Add the pages to the queue (a page already waiting stays once); the number of new entries."""
    wanted = list(dict.fromkeys(p for p in (normalize(path) for path in paths) if p))
    added = 0
    for start in range(0, len(wanted), CHUNK):
        chunk = wanted[start:start + CHUNK]
        waiting = set(db.scalars(select(IndexNowUrl.path).where(IndexNowUrl.path.in_(chunk))))
        now = utcnow()
        for path in chunk:
            if path not in waiting:
                db.add(IndexNowUrl(path=path, queued_at=now))
                added += 1
        db.flush()
    return added


def due(db: Session, now: datetime | None = None) -> bool:
    last = get_setting(db, 'indexnow_sent_at')
    return not last or (now or utcnow()) - datetime.fromisoformat(last) >= SEND_EVERY


def body(paths: list[str]) -> dict[str, Any]:
    host = settings.site_url.split('://', 1)[-1].rstrip('/')
    return {'host': host, 'key': settings.indexnow_key,
            'keyLocation': f'{settings.site_url}/{settings.indexnow_key}.txt',
            'urlList': [f'{settings.site_url}{path}' for path in paths]}


def send(session_factory: sessionmaker[Session], *, transport: httpx.BaseTransport | None = None) -> int:
    """One batch of the queue to Yandex; the sent addresses leave the queue. A refusal keeps them for the next try."""
    with session_factory.begin() as db:
        set_setting(db, 'indexnow_sent_at', utcnow().isoformat())
        paths = list(db.scalars(select(IndexNowUrl.path).order_by(IndexNowUrl.queued_at, IndexNowUrl.path)
                                .limit(BATCH)))
    if not paths:
        return 0
    with httpx.Client(timeout=30, transport=transport) as client:
        response = client.post(ENDPOINT, json=body(paths))
    if response.status_code not in (200, 202):
        event(logger, 'indexnow_refused', logging.WARNING, status=response.status_code, urls=len(paths),
              answer=response.text[:300])
        return 0
    with session_factory.begin() as db:
        for start in range(0, len(paths), CHUNK):
            db.execute(delete(IndexNowUrl).where(IndexNowUrl.path.in_(paths[start:start + CHUNK])))
    event(logger, 'indexnow_sent', urls=len(paths), status=response.status_code)
    return len(paths)


def sitemap_paths(client: httpx.Client, index_url: str) -> list[str]:
    """Every <loc> of the Sitemap index and its files, as paths; the English files are skipped."""
    def locs(url: str) -> list[str]:
        response = client.get(url)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        return [el.text.strip() for el in root.iter() if el.tag.endswith('loc') and el.text]

    out: list[str] = []
    for file_url in locs(index_url):
        if '/sitemaps/en-' in file_url:
            continue
        # The files are fetched where the index was: the storefront itself, not through the public address.
        local = re.sub(r'^https?://[^/]+', index_url.rsplit('/sitemap.xml', 1)[0], file_url)
        out.extend(re.sub(r'^https?://[^/]+', '', loc) for loc in locs(local))
    return out
