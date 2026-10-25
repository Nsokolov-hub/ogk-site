"""The import wizard and the journal of batches (ADM-04, IMP-02, IMP-06).

Upload → match the columns (the template is saved on the source) → preview with errors (a dry run) → run in the
background with progress → the journal: created, updated, errors, conflicts, errors as xlsx, rollback.
"""

import hashlib
import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.admin.audit import record
from app.admin.models import ImportUpload
from app.admin.security import StaffDep, requires
from app.catalog.importer import run
from app.catalog.importer.reader import UnreadableFile, read_rows
from app.catalog.importer.sources import FIELDS, REQUIRED, TEMPLATES
from app.catalog.models import ImportBatch, ImportIssue, ImportSource
from app.core.config import settings
from app.core.db import DB
from app.core.errors import DomainError
from app.outbox.models import OutboxEvent

router = APIRouter()
MAX_UPLOAD = 500 * 1024 * 1024
FIELD_NAMES = {'brand': 'Производитель', 'catalog_number': 'Каталожный номер', 'name': 'Наименование', 'cas': 'CAS',
               'pack': 'Фасовка', 'availability': 'Наличие', 'characteristics': 'Характеристики (формула и масса)'}


def upload_dir() -> Path:
    path = Path(settings.storage_dir) / 'imports'
    path.mkdir(parents=True, exist_ok=True)
    return path


def source_out(code: str, row: ImportSource | None) -> dict[str, Any]:
    template = TEMPLATES.get(code, {})
    return {'code': code, 'name': row.name if row else template.get('name', code),
            'mapping': row.mapping if row else template.get('mapping', {}),
            'options': row.options if row else template.get('options', {}), 'builtIn': code in TEMPLATES}


@router.get('/import/sources', dependencies=[requires('import.read')])
def sources(db: DB) -> dict[str, Any]:
    saved = {s.code: s for s in db.scalars(select(ImportSource))}
    codes = list(dict.fromkeys([*TEMPLATES, *saved]))
    return {'items': [source_out(c, saved.get(c)) for c in codes],
            'fields': [{'key': f, 'name': FIELD_NAMES.get(f, f), 'required': f in REQUIRED} for f in FIELDS]}


class SourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mapping: dict[str, str]
    options: dict[str, Any] = {}


@router.put('/import/sources/{code}', dependencies=[requires('import.write')])
def save_source(code: str, body: SourceIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Шаблон колонок сохраняется на источник (IMP-02): следующий файл того же поставщика узнаётся сам."""
    mapping = {k: v.strip() for k, v in body.mapping.items() if k in FIELDS and v.strip()}
    missing = [FIELD_NAMES[f] for f in REQUIRED if f not in mapping]
    if missing:
        raise DomainError('MAPPING_INCOMPLETE', f'Укажите колонки: {", ".join(missing)}', 422, 'mapping')
    row = db.scalar(select(ImportSource).where(ImportSource.code == code))
    before = source_out(code, row)
    if row is None:
        row = run.ensure_source(db, code) if code in TEMPLATES else ImportSource(code=code, name=body.name)
        if row.id is None:
            db.add(row)
    template_options = TEMPLATES.get(code, {}).get('options', {})
    row.name, row.mapping = body.name, mapping
    row.options = {**template_options, **{k: v for k, v in body.options.items() if k in template_options or
                                          k in ('names', 'availability', 'create_brands', 'group_pack_suffix',
                                                'full_source')}}
    db.flush()
    record(db, staff, 'import_source', code, 'update', row.name, before, source_out(code, row))
    return source_out(code, row)


@router.post('/import/uploads', dependencies=[requires('import.write')])
async def upload(staff: StaffDep, db: DB, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    name = (file.filename or 'file').replace('\\', '/').split('/')[-1][:250]
    suffix = Path(name).suffix.lower()
    if suffix not in ('.xlsx', '.csv'):
        raise DomainError('FILE_TYPE', 'Файл xlsx или csv', 422, 'file')
    key = f'{uuid4()}{suffix}'
    target = upload_dir() / key
    digest, size = hashlib.sha256(), 0
    with target.open('wb') as handle:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > MAX_UPLOAD:
                handle.close()
                target.unlink(missing_ok=True)
                raise DomainError('FILE_SIZE', 'Файл больше 500 МБ: разделите его', 413, 'file')
            digest.update(chunk)
            handle.write(chunk)
    try:
        reader = read_rows(target, name)
        header = [str(c or '') for c in next(reader, [])]
        sample = [row for _, row in zip(range(10), reader, strict=False)]
    except (UnreadableFile, StopIteration, ValueError) as exc:
        target.unlink(missing_ok=True)
        raise DomainError('FILE_UNREADABLE', f'Файл не читается: {exc}', 422, 'file') from None
    row = ImportUpload(file_name=name, storage_key=key, size=size, sha256=digest.hexdigest(), header=header,
                       sample=sample, author_name=staff.name)
    db.add(row)
    db.flush()
    return upload_out(db, row)


def suggest(db: DB, header: list[str]) -> list[dict[str, Any]]:
    """Sources whose column titles are in the file, the best first."""
    titles = {h.strip().casefold() for h in header if h}
    out = []
    for source in sources(db)['items']:
        found = [f for f, title in source['mapping'].items() if title.strip().casefold() in titles]
        if found:
            out.append({'code': source['code'], 'name': source['name'], 'matched': found,
                        'complete': all(f in found for f in REQUIRED)})
    return sorted(out, key=lambda s: (not s['complete'], -len(s['matched'])))


def upload_out(db: DB, row: ImportUpload) -> dict[str, Any]:
    batch = db.get(ImportBatch, row.batch_id) if row.batch_id else None
    return {'id': row.id, 'fileName': row.file_name, 'size': row.size, 'header': row.header, 'sample': row.sample,
            'status': row.status, 'source': row.source, 'dryRun': row.dry_run, 'batchId': row.batch_id,
            'error': row.error, 'createdAt': row.created_at.isoformat(), 'author': row.author_name,
            'suggested': suggest(db, row.header), 'batch': batch_out(db, batch) if batch else None}


@router.get('/import/uploads', dependencies=[requires('import.read')])
def uploads(db: DB) -> list[dict[str, Any]]:
    rows = db.scalars(select(ImportUpload).order_by(ImportUpload.created_at.desc()).limit(20))
    return [upload_out(db, r) for r in rows]


@router.get('/import/uploads/{upload_id}', dependencies=[requires('import.read')])
def upload_card(upload_id: str, db: DB) -> dict[str, Any]:
    row = db.get(ImportUpload, upload_id)
    if row is None:
        raise DomainError('NOT_FOUND', 'Файл не найден', 404)
    return upload_out(db, row)


class RunIn(BaseModel):
    source: str
    dryRun: bool = True


@router.post('/import/uploads/{upload_id}/run', dependencies=[requires('import.write')])
def start(upload_id: str, body: RunIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Предпросмотр (dryRun) или загрузка — в фоне; прогресс — в журнале партий."""
    row = db.scalar(select(ImportUpload).where(ImportUpload.id == upload_id).with_for_update())
    if row is None:
        raise DomainError('NOT_FOUND', 'Файл не найден', 404)
    if row.status in ('queued', 'running'):
        raise DomainError('IMPORT_RUNNING', 'Этот файл уже загружается', 409)
    if body.source not in TEMPLATES and db.scalar(select(ImportSource.id).where(ImportSource.code == body.source)) \
            is None:
        raise DomainError('SOURCE_UNKNOWN', 'Нет такого источника', 422, 'source')
    if db.scalar(select(func.count()).select_from(ImportUpload).where(ImportUpload.status.in_(('queued', 'running')))):
        raise DomainError('IMPORT_BUSY', 'Идёт другая загрузка: дождитесь её окончания', 409)
    row.status, row.source, row.dry_run, row.error, row.batch_id = 'queued', body.source, body.dryRun, None, None
    db.add(OutboxEvent(event_key=f'import:{row.id}:{row.version}', kind='import.run',
                       payload={'upload_id': row.id, 'author': staff.name}))
    row.version += 1
    record(db, staff, 'import', row.id, 'preview' if body.dryRun else 'run', f'{row.file_name} → {body.source}')
    db.flush()
    return upload_out(db, row)


def batch_out(db: DB, batch: ImportBatch) -> dict[str, Any]:
    source = db.get(ImportSource, batch.source_id)
    return {'id': batch.id, 'source': source.code if source else '', 'fileName': batch.file_name,
            'dryRun': batch.dry_run, 'status': batch.status, 'rowsDone': batch.rows_done,
            'rowsTotal': batch.rows_total, 'counters': batch.counters, 'error': batch.error, 'author': batch.author,
            'startedAt': batch.started_at.isoformat(),
            'finishedAt': batch.finished_at.isoformat() if batch.finished_at else None}


@router.get('/import/batches', dependencies=[requires('import.read')])
def batches(db: DB, page: int = 1) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(ImportBatch)) or 0
    rows = db.scalars(select(ImportBatch).order_by(ImportBatch.started_at.desc())
                      .offset((max(page, 1) - 1) * 30).limit(30))
    return {'total': total, 'items': [batch_out(db, b) for b in rows]}


@router.get('/import/batches/{batch_id}', dependencies=[requires('import.read')])
def batch_card(batch_id: str, db: DB, kind: str = '', page: int = 1) -> dict[str, Any]:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise DomainError('NOT_FOUND', 'Партия не найдена', 404)
    summary = [{'kind': k, 'code': c, 'count': n} for k, c, n in db.execute(
        select(ImportIssue.kind, ImportIssue.code, func.count()).where(ImportIssue.batch_id == batch_id)
        .group_by(ImportIssue.kind, ImportIssue.code).order_by(func.count().desc()))]
    statement = select(ImportIssue).where(ImportIssue.batch_id == batch_id)
    if kind:
        statement = statement.where(ImportIssue.kind == kind)
    issues = db.scalars(statement.order_by(ImportIssue.row_number).offset((max(page, 1) - 1) * 100).limit(100))
    return {**batch_out(db, batch), 'summary': summary, 'issues': [
        {'id': i.id, 'row': i.row_number, 'kind': i.kind, 'code': i.code, 'message': i.message, 'values': i.values,
         'productId': i.product_id, 'resolved': i.resolved} for i in issues]}


@router.get('/import/batches/{batch_id}/issues.xlsx', dependencies=[requires('import.read')])
def issues_xlsx(batch_id: str, db: DB) -> FileResponse:
    if db.get(ImportBatch, batch_id) is None:
        raise DomainError('NOT_FOUND', 'Партия не найдена', 404)
    path = Path(tempfile.mkdtemp()) / f'issues-{batch_id[:8]}.xlsx'
    run.export_issues(db, batch_id, path)
    return FileResponse(path, filename=path.name,
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@router.post('/import/batches/{batch_id}/rollback', dependencies=[requires('import.write')])
def rollback(batch_id: str, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Откат партии (IMP-06): созданные ею товары удаляются, изменённые получают прежние значения."""
    try:
        result = run.rollback(db, batch_id)
    except run.ImportFailed as exc:
        raise DomainError('ROLLBACK_REFUSED', str(exc), 409) from None
    record(db, staff, 'import', batch_id, 'rollback', f'удалено {result["deleted"]}, восстановлено {result["restored"]}')
    return result
