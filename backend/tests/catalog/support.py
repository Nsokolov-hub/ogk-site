"""Catalog test data: a small assortment file in the shape of the export of 17.10.2026, the business's catalog by
category (31.10.2026) and a fake engine."""

import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

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


CATALOG_HEADER = ['№', 'Направление', 'Категория', 'Подгруппа', 'Наименование', 'Кат. №', 'CAS', 'Производитель',
                  'Фасовка', 'Характеристики', 'Описание']


def workbook(path: Path, sheets: list[tuple[str, list[list[Any]]]]) -> Path:
    """An xlsx of several sheets with inline strings, as large exports are written."""
    ns = 'http://schemas.openxmlformats.org'

    def ref(col: int, row: int) -> str:
        letters, col = '', col + 1
        while col:
            col, rem = divmod(col - 1, 26)
            letters = chr(65 + rem) + letters
        return f'{letters}{row}'

    def cell(at: str, value: Any) -> str:
        if value is None or value == '':
            return ''
        if isinstance(value, int | float):
            return f'<c r="{at}"><v>{value}</v></c>'
        return f'<c r="{at}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'

    overrides = ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.'
                        f'openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets) + 1))
    files = {
        '[Content_Types].xml': f'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="{ns}/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{overrides}</Types>',
        '_rels/.rels': f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{ns}/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{ns}/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="{ns}/spreadsheetml/2006/main" '
        f'xmlns:r="{ns}/officeDocument/2006/relationships"><sheets>'
        + ''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _) in enumerate(sheets, 1))
        + '</sheets></workbook>',
        'xl/_rels/workbook.xml.rels': f'<?xml version="1.0" encoding="UTF-8"?><Relationships '
        f'xmlns="{ns}/package/2006/relationships">'
        + ''.join(f'<Relationship Id="rId{i}" Type="{ns}/officeDocument/2006/relationships/worksheet" '
                  f'Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets) + 1)) + '</Relationships>',
    }
    for i, (_, rows) in enumerate(sheets, 1):
        body = ''.join(f'<row r="{r}">' + ''.join(cell(ref(c, r), v) for c, v in enumerate(values)) + '</row>'
                       for r, values in enumerate(rows, 1))
        files[f'xl/worksheets/sheet{i}.xml'] = (f'<?xml version="1.0" encoding="UTF-8"?><worksheet '
                                                f'xmlns="{ns}/spreadsheetml/2006/main"><sheetData>{body}</sheetData>'
                                                '</worksheet>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def catalog_file(path: Path, sheets: dict[str, list[tuple[str, str, str, str, str, str | None, str, str | None]]]
                 ) -> Path:
    """The business's catalog by category: contents first, then a sheet per direction with a title row above the
    column titles. Rows: (direction, category, subgroup, name, catalog number, CAS, manufacturer, packaging)."""
    contents = [[None, 'Каталог продукции — что мы можем поставить'], [None, 'Направление', 'Позиций']]
    out: list[tuple[str, list[list[Any]]]] = [('Обзор', contents), ('Категории', [['Направление / категория']])]
    number = 0
    for name, rows in sheets.items():
        data: list[list[Any]] = [['← Оглавление', f'{name} · {len(rows)} позиций'], CATALOG_HEADER]
        for direction, category, subgroup, title, catalog_number, cas, maker, pack in rows:
            number += 1
            data.append([number, direction, category, subgroup, title, catalog_number, cas, maker, pack,
                         'Formula: C10H12N2O; Hazard: none', 'Текст описания источника'])
        out.append((name, data))
    return workbook(path, out)


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

    def exists(self, index: str) -> bool:
        return bool(self.settings)
