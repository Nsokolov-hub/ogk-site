"""Small HTML helpers; no browser, hidden endpoints, or site-wide stock inference.

Adapters are tested against semantic examples observed on the public pages. CSS classes are deliberately not
assumed: product tables are selected by their visible headers and availability is read in the same row/card.
"""

import hashlib
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from app.catalog.normalize import clean_spaces

_VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'wbr'}
_PRIVATE = re.compile(r'(?:search|personal|account|basket|cart|login|bitrix|include|filter|ajax)', re.I)


@dataclass(eq=False)
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list['Node | str'] = field(default_factory=list)
    parent: 'Node | None' = field(default=None, repr=False)

    def find(self, tag: str) -> list['Node']:
        return [child for child in self.walk() if child.tag == tag]

    def walk(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.walk()

    def text(self) -> str:
        if self.tag in {'script', 'style', 'noscript'}:
            return ''
        return clean_spaces(' '.join(child.text() if isinstance(child, Node) else child
                                     for child in self.children))


class Document(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node('document')
        self.stack = [self.root]
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        # HTML permits omitted table closing tags; keep each cell/row in its own scope.
        if tag in {'td', 'th'} and self.stack[-1].tag in {'td', 'th'}:
            self.stack.pop()
        if tag == 'tr':
            while self.stack[-1].tag in {'td', 'th', 'tr'}:
                self.stack.pop()
        node = Node(tag, dict((key, value or '') for key, value in attrs), parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def cells(row: Node) -> list[Node]:
    return [child for child in row.children if isinstance(child, Node) and child.tag in {'td', 'th'}]


def rows(table: Node) -> list[list[Node]]:
    return [value for row in table.find('tr') if (value := cells(row))]


def header_table(root: Node, required: tuple[str, ...], only: list[Node] | None = None):
    """Yield tables with the exact visible headings, including their data rows."""
    for table in root.find('table') if only is None else only:
        table_rows = rows(table)
        for index, row in enumerate(table_rows):
            headings = [cell.text().casefold().rstrip(':') for cell in row]
            if all(any(term in heading for heading in headings) for term in required):
                yield headings, table_rows[index + 1:]
                break


def public_url(href: str, current: str, prefixes: tuple[str, ...]) -> str | None:
    """Only same-origin observed catalogue paths; only observed pagination parameters survive."""
    target = urlsplit(urljoin(current, href))
    origin = urlsplit(current)
    if (target.scheme, target.netloc) != (origin.scheme, origin.netloc) or target.username or target.password:
        return None
    if _PRIVATE.search(target.path) or not any(target.path.startswith(prefix) for prefix in prefixes):
        return None
    query = parse_qsl(target.query, keep_blank_values=True)
    if query and not all(re.fullmatch(r'PAGEN_\d+', key) and value.isdigit() and int(value) > 0
                         for key, value in query):
        return None
    return urlunsplit((target.scheme, target.netloc, target.path, urlencode(sorted(query)), ''))


def links(root: Node, current: str, prefixes: tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys(url for anchor in root.find('a')
                              if (url := public_url(anchor.attrs.get('href', ''), current, prefixes)) and url != current))


def tasks(urls: list[str], source: str) -> tuple[list[dict], int]:
    return ([{'s': source, 'url': url, 'page': int(dict(parse_qsl(urlsplit(url).query)).get('PAGEN_1', '1'))}
             for url in urls], 0)


def identity(url: str, number: str, pack: str | None = None) -> str:
    return hashlib.sha256(f'{urlsplit(url).path}|{number}|{pack or ""}'.encode()).hexdigest()


def positive(value: str) -> tuple[bool, int | None]:
    match = re.fullmatch(r'(?:есть\s+)?в\s+наличии(?:\s*:\s*(\d+))?|на\s+складе(?:\s*:\s*(\d+))?',
                         clean_spaces(value).casefold())
    if not match:
        return False, None
    count = next((int(part) for part in match.groups() if part is not None), None)
    return count is None or count > 0, count


def negative(value: str) -> bool:
    value = clean_spaces(value).casefold()
    return bool(re.fullmatch(r'(?:нет|не)\s+в\s+наличии|под\s+заказ|нет\s+на\s+складе|в\s+транзите', value)
                or re.search(r'\d\s*(?:[-–—]\s*\d+)?\s*(?:нед|дн|день|месяц)', value))
