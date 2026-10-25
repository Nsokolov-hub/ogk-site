"""Long work of the admin panel in the worker process (ADM-04, ADM-10): an import batch or a re-count of the whole
catalog runs in a thread of its own, one at a time, while the worker keeps delivering requests and letters.

A worker restarted in the middle marks the interrupted upload as failed: the batch journal shows how far it got,
and the rollback undoes it.
"""

import logging
import threading
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.admin.models import ImportUpload, StaffSession
from app.catalog.importer import run
from app.catalog.models import ImportBatch
from app.catalog.settings import get_setting, set_setting
from app.core import storefront
from app.core.config import settings
from app.core.db import SessionLocal, utcnow
from app.core.logs import event

logger = logging.getLogger('site.jobs')
_lock = threading.Lock()
_running: threading.Thread | None = None


def busy() -> bool:
    return _running is not None and _running.is_alive()


def _start(target: Callable[[], None], name: str) -> bool:
    global _running
    with _lock:
        if busy():
            return False
        _running = threading.Thread(target=target, name=name, daemon=True)
        _running.start()
        return True


def start_import(upload_id: str, author: str, session_factory: sessionmaker[Session] | None = None,
                 wait: bool = False) -> bool:
    factory = session_factory or SessionLocal

    def work() -> None:
        run_import(factory, upload_id, author)

    if wait:
        work()
        return True
    if not _start(work, f'import-{upload_id[:8]}'):
        # Another long job is running: the upload waits and is taken by the next free run.
        with factory.begin() as db:
            db.execute(update(ImportUpload).where(ImportUpload.id == upload_id).values(status='queued'))
        threading.Timer(30, start_import, args=(upload_id, author, session_factory)).start()
        return False
    return True


def run_import(factory: sessionmaker[Session], upload_id: str, author: str) -> None:
    with factory.begin() as db:
        upload = db.get(ImportUpload, upload_id)
        if upload is None or upload.status not in ('queued',):
            return
        upload.status = 'running'
        path = Path(settings.storage_dir) / 'imports' / upload.storage_key
        source, dry_run, name = upload.source or 'price', upload.dry_run, upload.file_name
    try:
        result = run.import_files(factory, [path], source=source, dry_run=dry_run, author=author, names={path: name})
        batch_id = result['files'][0]['batch'] if result.get('files') else None
        with factory.begin() as db:
            db.execute(update(ImportUpload).where(ImportUpload.id == upload_id).values(
                status='done', batch_id=batch_id, error=None))
        if not dry_run:
            storefront.revalidate_catalog()
        event(logger, 'import_done', upload=upload_id, batch=batch_id, dry_run=dry_run)
    except Exception as exc:
        with factory.begin() as db:
            batch = db.scalar(select(ImportBatch).where(ImportBatch.file_name == name)
                              .order_by(ImportBatch.started_at.desc()).limit(1))
            db.execute(update(ImportUpload).where(ImportUpload.id == upload_id).values(
                status='failed', error=str(exc)[:2000], batch_id=batch.id if batch else None))
        event(logger, 'import_failed', logging.WARNING, upload=upload_id, error=str(exc)[:300])


def start_refresh(session_factory: sessionmaker[Session] | None = None, wait: bool = False) -> bool:
    factory = session_factory or SessionLocal

    def work() -> None:
        with factory.begin() as db:
            run.refresh_all(db)
        storefront.revalidate_catalog()
        event(logger, 'catalog_refreshed')

    if wait:
        work()
        return True
    return _start(work, 'catalog-refresh')


def recover_interrupted(factory: sessionmaker[Session]) -> int:
    """At worker start: uploads left «running» by a stopped worker are failed, their batches too."""
    with factory.begin() as db:
        stale = list(db.scalars(select(ImportUpload).where(ImportUpload.status == 'running')))
        for upload in stale:
            upload.status, upload.error = 'failed', 'Прервано перезапуском сервиса: откатите партию и загрузите снова'
        db.execute(update(ImportBatch).where(ImportBatch.status == 'running').values(
            status='failed', error='Прервано перезапуском сервиса', finished_at=utcnow()))
        queued = [u.id for u in db.scalars(select(ImportUpload).where(ImportUpload.status == 'queued'))]
    for upload_id in queued:
        start_import(upload_id, 'админка', factory)
    return len(stale)


def apply_search_settings(factory: sessionmaker[Session], engine_factory: Callable[[], Any]) -> bool:
    """New synonyms (substances, the dictionary) reach the index settings; documents stay as they are."""
    from app.catalog.search import indexer

    with factory() as db:
        if not get_setting(db, 'search_settings_dirty'):
            return False
    try:
        with factory.begin() as db:
            indexer.configure(db, engine_factory())
            set_setting(db, 'search_settings_dirty', False)
        return True
    except Exception as exc:
        event(logger, 'search_settings_failed', logging.WARNING, error=str(exc)[:200])
        return False


def prune_sessions(db: Session) -> int:
    result = db.execute(delete(StaffSession).where(StaffSession.expires_at < utcnow() - timedelta(days=7)))
    return int(getattr(result, 'rowcount', 0) or 0)
