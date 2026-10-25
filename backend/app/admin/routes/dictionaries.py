"""Dictionaries (ADM-06): units, storage conditions, search synonyms, the register of controlled substances.

Brands and substances have their own sections; the filters of a category are edited with the category.
"""

import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select

from app.admin.audit import record
from app.admin.editables import queue_revalidate
from app.admin.security import StaffDep, requires
from app.catalog import controlled
from app.catalog.importer.run import recheck_controlled
from app.catalog.models import ControlledEntry
from app.catalog.settings import get_setting, set_setting
from app.core.db import DB
from app.core.errors import DomainError

router = APIRouter()
KEYS = {'units': 'units', 'storage': 'storage_conditions', 'synonyms': 'search_synonyms'}


@router.get('/dictionaries', dependencies=[requires('dictionaries.read')])
def dictionaries(db: DB) -> dict[str, Any]:
    return {name: get_setting(db, key) for name, key in KEYS.items()}


class DictionaryIn(BaseModel):
    value: list[Any]


def check_entries(value: list[Any]) -> list[dict[str, str]]:
    out, keys = [], set()
    for number, item in enumerate(value, start=1):
        if not isinstance(item, dict) or not str(item.get('key') or '').strip() or not str(item.get('ru') or '').strip():
            raise DomainError('VALUE_INVALID', f'Строка {number}: нужны ключ и название', 422, 'value')
        key = str(item['key']).strip()
        if key in keys:
            raise DomainError('VALUE_INVALID', f'Ключ «{key}» повторяется', 422, 'value')
        keys.add(key)
        out.append({'key': key, 'ru': str(item['ru']).strip(), 'en': str(item.get('en') or item['ru']).strip()})
    return out


@router.put('/dictionaries/{name}', dependencies=[requires('dictionaries.write')])
def save(name: str, body: DictionaryIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    if name not in KEYS:
        raise DomainError('NOT_FOUND', 'Нет такого справочника', 404)
    if name == 'synonyms':
        # Groups of words that mean the same in search (SRCH-05): «окскарбазепин, oxcarbazepine».
        value: list[Any] = []
        for number, group in enumerate(body.value, start=1):
            words = [str(w).strip() for w in (group if isinstance(group, list) else str(group).split(',')) if str(w).strip()]
            if len(words) < 2:
                raise DomainError('VALUE_INVALID', f'Строка {number}: нужно хотя бы два слова', 422, 'value')
            value.append(words)
        set_setting(db, 'search_settings_dirty', True)
    else:
        value = check_entries(body.value)
    before = get_setting(db, KEYS[name])
    set_setting(db, KEYS[name], value)
    record(db, staff, 'setting', KEYS[name], 'update', f'справочник {name}', before, value)
    queue_revalidate(db, ['catalog'])
    return dictionaries(db)


@router.get('/dictionaries/controlled', dependencies=[requires('dictionaries.read')])
def register(db: DB, q: str = '', page: int = 1) -> dict[str, Any]:
    statement = select(ControlledEntry)
    if q.strip():
        statement = statement.where(ControlledEntry.name.ilike(f'%{q.strip()}%'))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(ControlledEntry.list_name, ControlledEntry.name)
                      .offset((max(page, 1) - 1) * 100).limit(100))
    return {'total': total, 'items': [{'id': r.id, 'list': r.list_name, 'name': r.name, 'cas': r.cas,
                                       'names': r.names} for r in rows]}


@router.post('/dictionaries/controlled', dependencies=[requires('dictionaries.write')])
async def upload_register(staff: StaffDep, db: DB, file: Annotated[UploadFile, File()]) -> dict[str, int]:
    """Перечни ПП № 681 и № 964 из xlsx (ТЗ 5.2.1): заменяют прежние, весь каталог перепроверяется."""
    path = Path(tempfile.mkdtemp()) / 'register.xlsx'
    path.write_bytes(await file.read(20 * 1024 * 1024))
    try:
        entries = controlled.read_register_xlsx(path)
    except Exception as exc:
        raise DomainError('FILE_UNREADABLE', f'Файл не читается: {exc}', 422, 'file') from None
    if not entries:
        raise DomainError('FILE_EMPTY', 'В файле нет строк перечней (колонки «Перечень», «Название», «CAS», «Синонимы»)',
                          422, 'file')
    count = controlled.load_register(db, entries)
    changed = recheck_controlled(db)
    record(db, staff, 'setting', 'controlled_register', 'upload', f'записей {count}, изменён признак у {changed}')
    return {'entries': count, 'changed': changed}
