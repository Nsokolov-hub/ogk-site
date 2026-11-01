"""Streaming readers of price lists: xlsx (shared or inline strings) and csv (encoding and delimiter detected).

The xlsx reader parses the sheet XML incrementally, so a file of 500 000 rows is read in seconds with flat
memory (IMP-07); openpyxl's read-only mode is several times slower on such files.

A workbook may hold contents or summaries before its data, and a title above the column titles: ``tables`` finds
the sheets whose first rows have the wanted column titles and yields each of them from its header on.
"""

import codecs
import csv
import io
import re
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import chain, islice
from pathlib import Path
from typing import IO
from xml.etree import ElementTree

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


class UnreadableFile(Exception):
    pass


def _column_index(ref: str) -> int:
    letters = re.match(r'[A-Z]+', ref)
    if not letters:
        return 0
    index = 0
    for ch in letters.group(0):
        index = index * 26 + (ord(ch) - 64)
    return index - 1


def _sheets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    """(sheet name, its XML part) in the workbook's order."""
    names = set(archive.namelist())
    found: list[tuple[str, str]] = []
    try:
        workbook = ElementTree.fromstring(archive.read('xl/workbook.xml'))
        rels = ElementTree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {rel.get('Id'): rel.get('Target', '').lstrip('/') for rel in rels}
        for sheet in workbook.iter(f'{NS}sheet'):
            target = targets.get(sheet.get(f'{REL_NS}id')) or ''
            path = target if target.startswith('xl/') else f'xl/{target}'
            if path in names:
                found.append((sheet.get('name') or path, path))
    except (KeyError, ElementTree.ParseError):
        pass
    if not found and 'xl/worksheets/sheet1.xml' in names:
        found.append(('sheet1', 'xl/worksheets/sheet1.xml'))
    if not found:
        raise UnreadableFile('В файле нет листа с данными')
    return found


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if 'xl/sharedStrings.xml' not in archive.namelist():
        return []
    strings: list[str] = []
    with archive.open('xl/sharedStrings.xml') as handle:
        for _event, element in ElementTree.iterparse(handle, events=('end',)):
            if element.tag == f'{NS}si':
                strings.append(''.join(t.text or '' for t in element.iter(f'{NS}t')))
                element.clear()
    return strings


def _sheet_rows(archive: zipfile.ZipFile, part: str, strings: list[str]) -> Iterator[list[str | None]]:
    with archive.open(part) as handle:
        for _event, element in ElementTree.iterparse(handle, events=('end',)):
            if element.tag != f'{NS}row':
                continue
            row: list[str | None] = []
            for cell in element:
                if cell.tag != f'{NS}c':
                    continue
                index = _column_index(cell.get('r', ''))
                kind = cell.get('t')
                if kind == 'inlineStr':
                    value: str | None = ''.join(t.text or '' for t in cell.iter(f'{NS}t'))
                else:
                    raw = cell.find(f'{NS}v')
                    value = raw.text if raw is not None else None
                    if kind == 's' and value is not None:
                        value = strings[int(value)] if int(value) < len(strings) else None
                    elif value is not None and kind not in ('str', 'e', 'b') and re.fullmatch(r'-?\d+\.0', value):
                        value = value[:-2]
                while len(row) < index:
                    row.append(None)
                row.append(value)
            yield row
            element.clear()


def _open_xlsx(source: Path | IO[bytes]) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(source)
    except zipfile.BadZipFile as exc:
        raise UnreadableFile('Файл не похож на xlsx') from exc


def read_xlsx(source: Path | IO[bytes]) -> Iterator[list[str | None]]:
    with _open_xlsx(source) as archive:
        yield from _sheet_rows(archive, _sheets(archive)[0][1], _shared_strings(archive))


def read_xlsx_sheets(source: Path | IO[bytes]) -> Iterator[tuple[str, Iterator[list[str | None]]]]:
    """Every sheet of a workbook in turn: (its name, its rows). Read each sheet's rows before taking the next."""
    with _open_xlsx(source) as archive:
        strings = _shared_strings(archive)
        for name, part in _sheets(archive):
            yield name, _sheet_rows(archive, part, strings)


def _decode(sample: bytes) -> str:
    for encoding in ('utf-8-sig', 'cp1251'):
        try:
            codecs.decode(sample, encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return 'latin-1'


def read_csv(source: Path | IO[bytes]) -> Iterator[list[str | None]]:
    handle = source.open('rb') if isinstance(source, Path) else source
    try:
        sample = handle.read(65536)
        handle.seek(0)
        encoding = _decode(sample[:65000])
        text = io.TextIOWrapper(handle, encoding=encoding, newline='')
        try:
            dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(codecs.decode(sample[:65000], encoding,
                                                                                         'ignore'), ';,\t|')
        except csv.Error:
            dialect = csv.excel
        for row in csv.reader(text, dialect):
            yield [cell if cell != '' else None for cell in row]
    finally:
        if isinstance(source, Path):
            handle.close()


def read_rows(source: Path | IO[bytes], name: str | None = None) -> Iterator[list[str | None]]:
    filename = (name or (source.name if isinstance(source, Path) else '')).casefold()
    if filename.endswith('.xlsx'):
        return read_xlsx(source)
    if filename.endswith(('.csv', '.txt', '.tsv')):
        return read_csv(source)
    raise UnreadableFile('Поддерживаются файлы xlsx и csv')


# Rows of a sheet looked at for the column titles: a title or a link back to the contents may stand above them.
HEADER_ROWS = 10


@dataclass
class Table:
    sheet: str | None
    header: list[str | None]
    rows: Iterator[list[str | None]]
    # The sheet's row number of the header (from 1); data rows follow it.
    header_row: int


def _titles(row: list[str | None]) -> set[str]:
    return {' '.join(str(cell).split()).casefold() for cell in row if cell}


def _table(sheet: str | None, rows: Iterator[list[str | None]], wanted: list[set[str]],
           fallback: bool) -> Table | None:
    head = list(islice(rows, HEADER_ROWS))
    for index, row in enumerate(head):
        titles = _titles(row)
        if any(want <= titles for want in wanted):
            return Table(sheet, row, chain(head[index + 1:], rows), index + 1)
    if fallback and head:
        return Table(sheet, head[0], chain(head[1:], rows), 1)
    return None


def tables(source: Path | IO[bytes], name: str | None = None, wanted: Iterable[Iterable[str]] = (),
           all_sheets: bool = False) -> Iterator[Table]:
    """Tables of a file, each from its header on; ``wanted`` — sets of column titles, any one of them makes a header.

    By default one table: in a workbook the first sheet with such a header (the first sheet when none has one), its
    header the first such row (the first row when none is). With ``all_sheets`` every sheet with a header, in order;
    sheets without one (contents, summaries) are left out. A csv file is one table.
    """
    want = [{' '.join(t.split()).casefold() for t in titles} for titles in wanted]
    want = [w for w in want if w]
    filename = (name or (source.name if isinstance(source, Path) else '')).casefold()
    if not filename.endswith('.xlsx'):
        table = _table(None, read_rows(source, name), want, fallback=True)
        if table:
            yield table
        return
    found = False
    for sheet, rows in read_xlsx_sheets(source):
        table = _table(sheet, rows, want, fallback=False)
        if table is None:
            continue
        found = True
        yield table
        if not all_sheets:
            return
    if not found:
        # No sheet has the wanted titles: the first sheet as it is, so the caller names the columns it misses.
        for sheet, rows in read_xlsx_sheets(source):
            table = _table(sheet, rows, [], fallback=True)
            if table:
                yield table
            return
