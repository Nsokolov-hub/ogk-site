"""Streaming readers of price lists: xlsx (shared or inline strings) and csv (encoding and delimiter detected).

The xlsx reader parses the sheet XML incrementally, so a file of 500 000 rows is read in seconds with flat
memory (IMP-07); openpyxl's read-only mode is several times slower on such files.
"""

import codecs
import csv
import io
import re
import zipfile
from collections.abc import Iterator
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


def _first_sheet(archive: zipfile.ZipFile) -> str:
    names = set(archive.namelist())
    try:
        workbook = ElementTree.fromstring(archive.read('xl/workbook.xml'))
        rels = ElementTree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        sheet = workbook.find(f'{NS}sheets/{NS}sheet')
        rel_id = sheet.get(f'{REL_NS}id') if sheet is not None else None
        for rel in rels:
            if rel.get('Id') == rel_id:
                target = rel.get('Target', '').lstrip('/')
                path = target if target.startswith('xl/') else f'xl/{target}'
                if path in names:
                    return path
    except (KeyError, ElementTree.ParseError):
        pass
    if 'xl/worksheets/sheet1.xml' in names:
        return 'xl/worksheets/sheet1.xml'
    raise UnreadableFile('В файле нет листа с данными')


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


def read_xlsx(source: Path | IO[bytes]) -> Iterator[list[str | None]]:
    try:
        archive = zipfile.ZipFile(source)
    except zipfile.BadZipFile as exc:
        raise UnreadableFile('Файл не похож на xlsx') from exc
    with archive:
        strings = _shared_strings(archive)
        with archive.open(_first_sheet(archive)) as handle:
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
