"""The journal of changes (ADM-01): who changed what, the state before and after, the way back to a version."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.models import AuditEntry


def record(db: Session, actor: Any, entity: str, entity_id: str, action: str, summary: str = '',
           before: Any = None, after: Any = None) -> AuditEntry:
    """``actor`` — the staff member (Staff) or None for the worker and commands."""
    entry = AuditEntry(actor_id=getattr(actor, 'id', None), actor_name=getattr(actor, 'name', None) or 'система',
                       entity=entity, entity_id=str(entity_id), action=action, summary=summary[:300],
                       before=before, after=after)
    db.add(entry)
    db.flush()
    return entry


def history(db: Session, entity: str, entity_id: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.scalars(select(AuditEntry).where(AuditEntry.entity == entity, AuditEntry.entity_id == str(entity_id))
                      .order_by(AuditEntry.id.desc()).limit(limit))
    return [entry_out(row) for row in rows]


def entry_out(row: AuditEntry, with_states: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {'id': row.id, 'at': row.at.isoformat(), 'actor': row.actor_name, 'entity': row.entity,
                           'entityId': row.entity_id, 'action': row.action, 'summary': row.summary,
                           'restorable': row.after is not None}
    if with_states:
        out.update(before=row.before, after=row.after)
    return out


def changed_fields(before: dict[str, Any] | None, after: dict[str, Any] | None) -> list[str]:
    before, after = before or {}, after or {}
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
