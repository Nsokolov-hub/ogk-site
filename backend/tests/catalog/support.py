"""Catalog test data: a small assortment file in the shape of the export of 17.10.2026 and a fake engine."""

from pathlib import Path
from typing import Any

from app.catalog.importer.run import write_xlsx
from app.catalog.search.engine import Query, Result

HEADER = ['№', 'Наименование', 'Кат. №', 'CAS', 'Производитель', 'Фасовка', 'Цена', 'Валюта', 'Наличие', 'Остаток',
          'Раздел (по прайсу)', 'Характеристики', 'Описание', 'Ссылка', 'ID']


SOURCE_LINK = 'https://chimmed-new.ru/products/item-id='
SOURCE_ID = 6263000


def assortment(path: Path, rows: list[tuple[str, str, str | None, str, str | None]],
               characteristics: dict[int, str] | None = None) -> Path:
    """Rows: (name, catalog number, CAS, manufacturer, packaging); the rest as in the export, with the source's
    links and ids in «Ссылка» and «ID» (they must never reach the catalog)."""
    data: list[list[Any]] = [HEADER]
    for i, (name, number, cas, maker, pack) in enumerate(rows, start=1):
        data.append([i, name, number, cas, maker, pack, 'по запросу', None, 'Под заказ', None, None,
                     (characteristics or {}).get(i, 'HS code: 29147990'), 'Текст описания источника',
                     f'{SOURCE_LINK}{SOURCE_ID + i}', SOURCE_ID + i])
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
