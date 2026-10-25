"""The journal of all changes (ADM-01): who, when, what, the state before and after."""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, or_, select

from app.admin.audit import entry_out
from app.admin.models import AuditEntry
from app.admin.security import requires
from app.core.db import DB
from app.core.errors import DomainError

router = APIRouter()


@router.get('/audit', dependencies=[requires('audit.read')])
def journal(db: DB, entity: str = '', entity_id: str = '', actor: str = '', q: str = '',
            page: int = 1) -> dict[str, Any]:
    statement = select(AuditEntry)
    if entity:
        statement = statement.where(AuditEntry.entity == entity)
    if entity_id:
        statement = statement.where(AuditEntry.entity_id == entity_id)
    if actor:
        statement = statement.where(AuditEntry.actor_name.ilike(f'%{actor}%'))
    if q.strip():
        statement = statement.where(or_(AuditEntry.summary.ilike(f'%{q.strip()}%'),
                                        AuditEntry.entity_id == q.strip()))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(AuditEntry.id.desc()).offset((max(page, 1) - 1) * 100).limit(100))
    return {'total': total, 'items': [entry_out(r) for r in rows]}


@router.get('/audit/{entry_id}', dependencies=[requires('audit.read')])
def entry(entry_id: int, db: DB) -> dict[str, Any]:
    row = db.get(AuditEntry, entry_id)
    if row is None:
        raise DomainError('NOT_FOUND', 'Запись не найдена', 404)
    return entry_out(row, with_states=True)
