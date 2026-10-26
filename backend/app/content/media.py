"""Media of the catalog at the site's own address (app.core.files): 2D structures, photos and documents.

Keys are content-addressed, so an answer never changes and is cached for a year. An SVG opened by itself runs
nothing: the answer carries a sandboxing CSP.
"""

from pathlib import PurePosixPath

from fastapi import APIRouter, Response

from app.core import files
from app.core.errors import DomainError

router = APIRouter(include_in_schema=False)
TYPES = {'.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
         '.webp': 'image/webp', '.pdf': 'application/pdf'}


@router.get('/media/{key:path}')
def media(key: str) -> Response:
    media_type = TYPES.get(PurePosixPath(key).suffix.lower())
    if media_type is None:
        raise DomainError('NOT_FOUND', 'Файл не найден', 404)
    try:
        data = files.storage().get(f'media/{key}')
    except files.FileMissing:
        raise DomainError('NOT_FOUND', 'Файл не найден', 404) from None
    except files.StorageUnavailable:
        raise DomainError('TEMPORARILY_UNAVAILABLE', 'Файл временно недоступен', 503) from None
    return Response(data, media_type=media_type, headers={
        'Cache-Control': 'public, max-age=31536000, immutable', 'X-Content-Type-Options': 'nosniff',
        'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; sandbox"})
