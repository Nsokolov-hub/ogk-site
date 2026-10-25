"""The search engine behind one interface (TZ 6: Meilisearch now, OpenSearch possible later).

Only this package knows the engine. The rest of the code builds ``Query`` objects and reads ``Result``.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


class EngineUnavailable(Exception):
    """The engine did not answer: the storefront shows an error, the indexer retries later."""


@dataclass
class Query:
    q: str = ''
    filter: str | None = None
    facets: list[str] = field(default_factory=list)
    sort: list[str] = field(default_factory=list)
    offset: int = 0
    limit: int = 20
    # Search these attributes only (catalog numbers and CAS for number-like queries).
    attributes: list[str] | None = None
    matching_strategy: str = 'last'
    fields: list[str] | None = None


@dataclass
class Result:
    hits: list[dict[str, Any]]
    total: int
    facets: dict[str, dict[str, int]] = field(default_factory=dict)


class SearchEngine(Protocol):
    def configure(self, index: str, settings: dict[str, Any]) -> None: ...

    def upsert(self, index: str, documents: list[dict[str, Any]]) -> None: ...

    def delete(self, index: str, ids: list[str]) -> None: ...

    def search(self, index: str, queries: list[Query]) -> list[Result]: ...

    def swap(self, index: str, other: str) -> None: ...

    def drop(self, index: str) -> None: ...

    def wait(self, timeout: float = 600.0) -> None: ...

    def count(self, index: str) -> int: ...

    def exists(self, index: str) -> bool: ...


def quote(value: str) -> str:
    """A string literal for filter expressions."""
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def any_of(attribute: str, values: list[str]) -> str:
    return '(' + ' OR '.join(f'{attribute} = {quote(v)}' for v in values) + ')'
