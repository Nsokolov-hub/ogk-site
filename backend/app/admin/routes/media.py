"""Photos and documents of cards uploaded in the admin panel (ADM-02): kept in the site's storage (local disk or S3,
app.core.files) and served at /api/v1/media/…, so a card never depends on a manufacturer's server.

The type is checked by content; SVG is not accepted from people (it can carry scripts), only drawn by the site.
"""

import hashlib
from typing import Annotated, Any

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.admin.audit import record
from app.admin.security import StaffDep, requires
from app.core import files
from app.core.config import settings
from app.core.db import DB
from app.core.errors import DomainError

router = APIRouter()


def sniff(head: bytes) -> tuple[str, str] | None:
    """(extension, media type) by the first bytes."""
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png', 'image/png'
    if head.startswith(b'\xff\xd8\xff'):
        return 'jpg', 'image/jpeg'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp', 'image/webp'
    if head.startswith(b'%PDF-'):
        return 'pdf', 'application/pdf'
    return None


@router.post('/media', dependencies=[requires('products.write')])
async def upload(staff: StaffDep, db: DB, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """Файл для карточки: фото (PNG, JPEG, WebP) или документ (PDF); ответ — адрес для карточки."""
    data = await file.read(settings.max_media_bytes + 1)
    if len(data) > settings.max_media_bytes:
        raise DomainError('FILE_SIZE', f'Файл больше {settings.max_media_bytes // (1024 * 1024)} МБ', 413, 'file')
    kind = sniff(data[:16])
    if not data or kind is None:
        raise DomainError('FILE_TYPE', 'Допустимы PNG, JPEG, WebP и PDF', 422, 'file')
    extension, media_type = kind
    if extension == 'pdf' and b'%%EOF' not in data[-4096:]:
        raise DomainError('FILE_CONTENT', 'PDF повреждён или не дописан', 422, 'file')
    digest = hashlib.sha256(data).hexdigest()
    folder = 'documents' if extension == 'pdf' else 'photos'
    key = f'media/{folder}/{digest[:2]}/{digest}.{extension}'
    store = files.storage()
    try:
        if not await run_in_threadpool(store.exists, key):
            await run_in_threadpool(store.put, key, data, media_type)
    except files.StorageUnavailable:
        raise DomainError('STORAGE_UNAVAILABLE', 'Хранилище файлов не отвечает, повторите позже', 503) from None
    name = (file.filename or '').replace('\\', '/').split('/')[-1][:250]
    record(db, staff, 'media', digest, 'upload', f'{name} ({len(data)} байт)', after={'key': key})
    return {'url': files.media_url(key), 'mediaType': media_type, 'size': len(data), 'name': name}
