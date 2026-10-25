"""Catalog test data: a small assortment file in the shape of the export of 17.10.2026 and a fake engine."""

from pathlib import Path
from typing import Any

from app.catalog.importer.run import write_xlsx
from app.catalog.search.engine import Query, Result

HEADER = ['№', 'Наименование', 'Кат. №', 'CAS', 'Производитель', 'Фасовка', 'Цена', 'Валюта', 'Наличие', 'Остаток',
          'Раздел (по прайсу)', 'Характеристики', 'Описание', 'Ссылка', 'ID']


def assortment(path: Path, rows: list[tuple[str, str, str | None, str, str | None]]) -> Path:
    """Rows: (name, catalog number, CAS, manufacturer, packaging); the rest as in the export."""
    data: list[list[Any]] = [HEADER]
    for i, (name, number, cas, maker, pack) in enumerate(rows, start=1):
        data.append([i, name, number, cas, maker, pack, 'по запросу', None, 'Под заказ', None, None,
                     'HS code: 29147990', 'Текст источника', f'https://example.test/p{i}', 1000 + i])
    write_xlsx(path, data)
    return path


class FakeEngine:
    """Records what the indexer sends; search is not supported."""

    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}
        self.deleted: list[str] = []
        self.settings: dict[str, Any] = {}

    def configure(self, index: str, settings: dict[str, Any]) -> None:
        self.settings = settings

    def upsert(self, index: str, documents: list[dict[str, Any]]) -> None:
        self.documents.update({d['id']: d for d in documents})

    def delete(self, index: str, ids: list[str]) -> None:
        self.deleted.extend(ids)
        for i in ids:
            self.documents.pop(i, None)

    def search(self, index: str, queries: list[Query]) -> list[Result]:
        raise NotImplementedError

    def swap(self, index: str, other: str) -> None: ...

    def drop(self, index: str) -> None: ...

    def wait(self, timeout: float = 600.0) -> None: ...

    def count(self, index: str) -> int:
        return len(self.documents)
