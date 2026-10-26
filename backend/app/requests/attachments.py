"""Customer attachments: XLSX, CSV, PDF, DOCX up to 10 MB (RFQ-03).

The type is checked by content, not only by name, as in the CRM; the CRM also scans every file with ClamAV
when it arrives. Files stay in private storage (local disk or S3, app.core.files) until the request is delivered.
"""

import hashlib
import io
import re
import zipfile
from pathlib import Path
from uuid import uuid4

from app.core import files
from app.core.config import settings
from app.core.errors import DomainError

TYPES = {
    '.pdf': 'application/pdf',
    '.csv': 'text/csv',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


def safe_name(name: str) -> str:
    return re.sub(r'[\x00-\x1f\x7f]', '', name.replace('\\', '/').split('/')[-1]).strip()[:250]


def content_matches(extension: str, content: bytes) -> bool:
    if extension == '.pdf':
        return content.startswith(b'%PDF-') and b'%%EOF' in content[-4096:]
    if extension == '.csv':
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('cp1251')
            except UnicodeDecodeError:
                return False
        return '\x00' not in text and not re.search(r'<\s*(?:!doctype\s+html|html|script|svg|iframe)\b', text, re.I)
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            member = 'xl/workbook.xml' if extension == '.xlsx' else 'word/document.xml'
            return ('[Content_Types].xml' in names and member in names and len(names) <= 5000
                    and sum(item.file_size for item in archive.infolist()) <= 100 * 1024 * 1024
                    and not any('vbaproject' in item.lower() or item.startswith('/') or '..' in item.split('/')
                                for item in names)
                    and not any(item.flag_bits & 1 for item in archive.infolist()))
    except (zipfile.BadZipFile, OSError):
        return False


def validate(name: str, content: bytes) -> tuple[str, str]:
    """(safe file name, media type) or a DomainError for the form's attachment field."""
    filename = safe_name(name)
    extension = Path(filename).suffix.lower()
    if not filename or extension not in TYPES:
        raise DomainError('FILE_TYPE', 'Допустимы файлы XLSX, CSV, PDF и DOCX', 422, 'attachment')
    if not content:
        raise DomainError('FILE_EMPTY', 'Файл пуст', 422, 'attachment')
    if len(content) > settings.max_attachment_bytes:
        raise DomainError('FILE_SIZE', 'Размер файла — не больше 10 МБ', 413, 'attachment')
    if not content_matches(extension, content):
        raise DomainError('FILE_CONTENT', 'Содержимое файла не соответствует его формату', 422, 'attachment')
    return filename, TYPES[extension]


def store(content: bytes) -> tuple[str, str]:
    """Write the file once to private storage (app.core.files); returns (storage key, SHA-256)."""
    file_id = uuid4().hex
    key = f'attachments/{file_id[:2]}/{file_id}'
    try:
        files.storage().put(key, content, 'application/octet-stream')
    except files.StorageUnavailable:
        raise DomainError('FILE_UNAVAILABLE', 'Не удалось сохранить вложение. Повторите отправку', 503) from None
    return key, hashlib.sha256(content).hexdigest()


def read(key: str, checksum: str) -> bytes:
    try:
        data = files.storage().get(key)
    except (files.FileMissing, files.StorageUnavailable):
        raise DomainError('FILE_UNAVAILABLE', 'Файл вложения недоступен', 503) from None
    if hashlib.sha256(data).hexdigest() != checksum:
        raise DomainError('FILE_INTEGRITY', 'Нарушена целостность файла вложения', 503)
    return data
