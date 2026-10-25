"""Keeping the index in step with PostgreSQL.

- ``index_pending`` — the queue: products with ``needs_index`` go to the engine in batches; the worker runs it
  every few seconds, so a change is searchable within a minute.
- ``reindex_all`` — a full rebuild without downtime: a new index is filled and swapped with the live one.
"""

import logging
import time
from collections.abc import Callable

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.catalog.models import Product
from app.catalog.search import documents
from app.catalog.search.engine import SearchEngine
from app.catalog.settings import get_setting
from app.core.config import settings
from app.core.db import utcnow
from app.core.logs import event

logger = logging.getLogger('site.search')
BATCH = 1000


def configure(db: Session, engine: SearchEngine, index: str | None = None) -> None:
    engine.configure(index or settings.meili_index, documents.index_settings(db))


def index_pending(db: Session, engine: SearchEngine, limit: int = BATCH, changed: list[str] | None = None) -> int:
    """Push one batch of queued products; the rows stay locked until the caller commits.

    ``changed`` collects the slugs, so the caller can drop the storefront's cached pages of these products.
    """
    products = db.scalars(select(Product).where(Product.needs_index.is_(True)).order_by(Product.id).limit(limit)
                          .with_for_update(skip_locked=True)).all()
    if not products:
        return 0
    if changed is not None:
        changed.extend(p.slug for p in products)
    ctx = documents.Context(db, get_setting(db, 'hide_controlled'))
    docs, deleted = documents.build(db, list(products), ctx)
    engine.upsert(settings.meili_index, docs)
    engine.delete(settings.meili_index, deleted)
    db.execute(update(Product).where(Product.id.in_([p.id for p in products])).values(needs_index=False))
    return len(products)


def reindex_all(db_factory: Callable[[], Session], engine: SearchEngine,
                progress: Callable[[int], None] | None = None) -> int:
    """Fill «<index>_next» from PostgreSQL, swap it with the live index, drop the old one."""
    live, staging = settings.meili_index, f'{settings.meili_index}_next'
    engine.drop(staging)
    with db_factory() as db:
        configure(db, engine, staging)
        configure(db, engine, live)
        ctx = documents.Context(db, get_setting(db, 'hide_controlled'))
    started, total, last_id = time.monotonic(), 0, ''
    began = utcnow()
    while True:
        with db_factory() as db:
            products = db.scalars(select(Product).where(Product.id > last_id).order_by(Product.id)
                                  .limit(5000)).all()
            if not products:
                break
            docs, _ = documents.build(db, list(products), ctx)
            engine.upsert(staging, docs)
            last_id = products[-1].id
            total += len(docs)
        if progress:
            progress(total)
    engine.wait(timeout=6 * 3600)
    engine.swap(live, staging)
    engine.drop(staging)
    # The rebuilt index has everything changed before it began; products changed meanwhile stay queued.
    with db_factory() as db, db.begin():
        db.execute(update(Product).where(Product.needs_index.is_(True), Product.updated_at < began)
                   .values(needs_index=False))
    event(logger, 'search_reindexed', documents=total, seconds=round(time.monotonic() - started))
    return total
