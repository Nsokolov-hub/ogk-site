"""Meilisearch over its HTTP API (httpx, no SDK): the only module that knows Meilisearch."""

import time
from typing import Any

import httpx

from app.catalog.search.engine import EngineUnavailable, Query, Result
from app.core.config import settings


class Meilisearch:
    def __init__(self, url: str | None = None, key: str | None = None, timeout: float | None = None,
                 transport: httpx.BaseTransport | None = None):
        self.client = httpx.Client(base_url=(url or settings.meili_url).rstrip('/'),
                                   headers={'Authorization': f'Bearer {key or settings.meili_key}'},
                                   timeout=timeout or settings.search_timeout_seconds, transport=transport)

    def _call(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise EngineUnavailable(f'{type(exc).__name__}: {exc}') from exc
        if response.status_code == 404 and method == 'DELETE':
            return None
        if response.status_code >= 400:
            raise EngineUnavailable(f'{response.status_code}: {response.text[:300]}')
        return response.json() if response.content else None

    def configure(self, index: str, index_settings: dict[str, Any]) -> None:
        self.create(index)
        self._task(self._call('PATCH', f'/indexes/{index}/settings', json=index_settings), timeout=600)

    def exists(self, index: str) -> bool:
        return self._exists(index)

    def _exists(self, index: str) -> bool:
        try:
            response = self.client.get(f'/indexes/{index}')
        except httpx.HTTPError as exc:
            raise EngineUnavailable(str(exc)) from exc
        return response.status_code == 200

    def upsert(self, index: str, documents: list[dict[str, Any]]) -> None:
        if documents:
            self._call('POST', f'/indexes/{index}/documents', json=documents, params={'primaryKey': 'id'})

    def delete(self, index: str, ids: list[str]) -> None:
        if ids:
            self._call('POST', f'/indexes/{index}/documents/delete-batch', json=ids)

    def search(self, index: str, queries: list[Query]) -> list[Result]:
        body = {'queries': [self._query(index, q) for q in queries]}
        answer = self._call('POST', '/multi-search', json=body)
        return [Result(hits=r.get('hits', []), total=int(r.get('totalHits', r.get('estimatedTotalHits', 0)) or 0),
                       facets=r.get('facetDistribution') or {}) for r in answer['results']]

    @staticmethod
    def _query(index: str, q: Query) -> dict[str, Any]:
        body: dict[str, Any] = {'indexUid': index, 'q': q.q, 'offset': q.offset, 'limit': q.limit,
                                'matchingStrategy': q.matching_strategy}
        if q.filter:
            body['filter'] = q.filter
        if q.facets:
            body['facets'] = q.facets
        if q.sort:
            body['sort'] = q.sort
        if q.attributes:
            body['attributesToSearchOn'] = q.attributes
        if q.fields:
            body['attributesToRetrieve'] = q.fields
        return body

    def swap(self, index: str, other: str) -> None:
        self._task(self._call('POST', '/swap-indexes', json=[{'indexes': [index, other]}]))

    def drop(self, index: str) -> None:
        if not self._exists(index):
            return
        answer = self._call('DELETE', f'/indexes/{index}')
        if answer:
            self._task(answer)

    def count(self, index: str) -> int:
        answer = self._call('GET', f'/indexes/{index}/stats')
        return int(answer.get('numberOfDocuments', 0))

    def create(self, index: str) -> None:
        if not self._exists(index):
            self._task(self._call('POST', '/indexes', json={'uid': index, 'primaryKey': 'id'}))

    def _task(self, answer: dict[str, Any] | None, timeout: float = 120.0) -> None:
        if not answer or 'taskUid' not in answer:
            return
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            task = self._call('GET', f'/tasks/{answer["taskUid"]}')
            if task['status'] == 'succeeded':
                return
            if task['status'] in ('failed', 'canceled'):
                raise EngineUnavailable(f'task {answer["taskUid"]}: {task.get("error")}')
            time.sleep(0.1)
        raise EngineUnavailable(f'task {answer["taskUid"]} did not finish in {timeout} s')

    def wait(self, timeout: float = 600.0) -> None:
        """Until every enqueued task is processed (tests and the full reindex)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            answer = self._call('GET', '/tasks', params={'statuses': 'enqueued,processing', 'limit': 1})
            if not answer.get('results'):
                return
            time.sleep(0.2)
        raise EngineUnavailable(f'tasks did not finish in {timeout} s')


_engine: Meilisearch | None = None


def engine() -> Meilisearch:
    global _engine
    if _engine is None:
        _engine = Meilisearch()
    return _engine
