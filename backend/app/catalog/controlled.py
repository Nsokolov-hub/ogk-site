"""Controlled substances (TZ 5.2.1): lists of Government Decrees No. 681 and No. 964.

A product is checked by CAS and by names on import and on edit. A CAS match marks it at once; a match by name
only (salts, isotope-labelled forms, a missing CAS) goes to the chemist for review. Marked products are hidden
from the storefront, search, Sitemap and the feed while the setting ``hide_controlled`` is on.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.catalog.models import ControlledEntry
from app.catalog.normalize import cas_or_none, clean_spaces


def _words(value: str) -> set[str]:
    return set(re.findall(r'[a-zа-яё0-9]+', value.casefold()))


@dataclass
class Register:
    by_cas: dict[str, str] = field(default_factory=dict)
    # A name of one or more words → list; matched when all its words are in the product name.
    names: list[tuple[frozenset[str], str]] = field(default_factory=list)

    @classmethod
    def load(cls, db: Session) -> 'Register':
        register = cls()
        for entry in db.scalars(select(ControlledEntry)):
            for cas in entry.cas:
                register.by_cas[cas] = entry.list_name
            for name in entry.names:
                words = frozenset(_words(name))
                if words:
                    register.names.append((words, entry.list_name))
        return register

    def match(self, name: str, cas: str | None, synonyms: list[str] | tuple[str, ...] = ()) -> tuple[str, str] | None:
        """(list, state): state «auto» for a CAS match, «review» for a match by name only."""
        if cas and cas in self.by_cas:
            return self.by_cas[cas], 'auto'
        texts = [_words(text) for text in (name, *synonyms) if text]
        for words, listed in self.names:
            if any(words <= text for text in texts):
                return listed, 'review'
        return None


def apply(register: Register, *, name: str, cas: str | None, synonyms: list[str], current: str | None,
          state: str | None) -> tuple[str | None, str | None]:
    """The new (controlled, controlled_state) of a product; the chemist's decision is never overwritten."""
    if state in ('confirmed', 'cleared'):
        return current, state
    hit = register.match(name, cas, synonyms)
    return (hit[0], hit[1]) if hit else (None, None)


def load_register(db: Session, entries: list[dict[str, Any]]) -> int:
    """Replace the register: [{"list": "pp681", "name": ..., "cas": [...], "names": [...]}]."""
    db.execute(delete(ControlledEntry))
    count = 0
    for raw in entries:
        listed = str(raw.get('list') or '')
        if listed not in ('pp681', 'pp964'):
            raise ValueError(f'Неизвестный перечень: {listed!r}')
        names = [clean_spaces(str(n)).casefold() for n in raw.get('names') or [] if clean_spaces(str(n))]
        cas = [c for c in (cas_or_none(str(v)) for v in raw.get('cas') or []) if c]
        db.add(ControlledEntry(list_name=listed, name=str(raw.get('name') or (names[0] if names else cas[0])),
                               cas=cas, names=names))
        count += 1
    db.flush()
    return count


def read_register_xlsx(path: Path) -> list[dict[str, Any]]:
    """Rows of a register file: columns «Перечень» (681/964), «Название», «CAS», «Синонимы» (через «;»)."""
    from app.catalog.importer.reader import read_rows

    entries = []
    rows = read_rows(path)
    header = [clean_spaces(str(cell)).casefold() for cell in next(rows)]

    def column(*names: str) -> int:
        for i, title in enumerate(header):
            if any(title.startswith(name) for name in names):
                return i
        raise ValueError(f'В файле нет колонки «{names[0]}»')

    listed, title, cas, synonyms = column('перечень', 'list'), column('назван', 'name'), column('cas'), \
        column('синоним', 'synonym')
    def value(row: list[str | None], i: int) -> str:
        return clean_spaces(str(row[i])) if i < len(row) and row[i] is not None else ''

    for row in rows:
        code = 'pp964' if '964' in value(row, listed) else 'pp681'
        name = value(row, title)
        if not name:
            continue
        entries.append({'list': code, 'name': name, 'cas': re.split(r'[;,\s]+', value(row, cas)),
                        'names': [name, *[s for s in value(row, synonyms).split(';') if s.strip()]]})
    return entries
