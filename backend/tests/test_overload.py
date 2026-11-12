"""Overload protection of the API (app.core.overload, incident of 12.11.2026)."""

import asyncio
import time
from collections import Counter
from collections.abc import Generator
from pathlib import Path
from typing import Annotated

import anyio
import httpx
from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings
from app.core.overload import LoadShedding


class Out(BaseModel):
    n: int


def toy_api(tmp_path: Path, *, guard: dict[str, int] | None, queue: int = 50, wait: float = 5.0,
            delay: float = 0.05) -> FastAPI:
    """The shape of the site's API: a synchronous endpoint, the session as a synchronous dependency with
    scope='function' and a response model — with a pool of two connections."""
    engine = create_engine(f'sqlite:///{tmp_path / "toy.db"}', poolclass=QueuePool, pool_size=2, max_overflow=0,
                           pool_timeout=2, connect_args={'check_same_thread': False})
    sessions = sessionmaker(engine)

    def get_db() -> Generator[Session]:
        with sessions() as session:
            yield session
            session.commit()

    app = FastAPI()

    @app.get('/api/v1/public/x', response_model=Out)
    def x(db: Annotated[Session, Depends(get_db, scope='function')]):
        n = db.execute(text('SELECT 1')).scalar_one()
        time.sleep(delay)
        return {'n': n}

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    if guard is not None:
        app.add_middleware(LoadShedding, limits=guard, queue=queue, wait=wait)
    return app


async def burst(app: FastAPI, count: int, path: str = '/api/v1/public/x') -> tuple[Counter, float, list[httpx.Response]]:
    # Six threads instead of forty: the same proportion to the pool as on the server, but quick.
    anyio.to_thread.current_default_thread_limiter().total_tokens = 6
    responses: list[httpx.Response] = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                 base_url='http://test', timeout=60) as client:
        started = time.perf_counter()

        async def one() -> int | str:
            try:
                response = await client.get(path)
            except Exception as exc:
                return type(exc).__name__
            responses.append(response)
            return response.status_code

        statuses = Counter(await asyncio.gather(*[one() for _ in range(count)]))
        return statuses, time.perf_counter() - started, responses


def test_without_the_guard_a_burst_locks_threads_and_connections(tmp_path):
    # The incident itself: 20 requests at once, two connections, six threads — most fail on the pool timeout.
    statuses, _, _ = asyncio.run(burst(toy_api(tmp_path, guard=None), 20))
    assert statuses[200] < 20


def test_the_guard_lets_a_burst_through(tmp_path):
    statuses, seconds, _ = asyncio.run(burst(toy_api(tmp_path, guard={'': 2}), 20))
    assert statuses == Counter({200: 20})
    assert seconds < 5


def test_a_full_queue_is_refused_at_once_with_retry_after(tmp_path):
    app = toy_api(tmp_path, guard={'': 1}, queue=2, wait=5.0, delay=0.3)
    statuses, seconds, responses = asyncio.run(burst(app, 10))
    assert statuses[200] == 3 and statuses[503] == 7
    refused = next(r for r in responses if r.status_code == 503)
    assert refused.json()['code'] == 'OVERLOADED'
    assert refused.headers['retry-after'] == '5'
    assert refused.headers['cache-control'] == 'no-store'
    assert seconds < 3


def test_a_long_wait_is_refused_after_the_limit(tmp_path):
    app = toy_api(tmp_path, guard={'': 1}, queue=50, wait=0.2, delay=0.5)
    statuses, seconds, _ = asyncio.run(burst(app, 4))
    assert statuses == Counter({200: 1, 503: 3})
    assert seconds < 2


def test_health_is_never_queued(tmp_path):
    app = toy_api(tmp_path, guard={'': 1}, queue=0, wait=0.1, delay=0.5)

    async def both():
        anyio.to_thread.current_default_thread_limiter().total_tokens = 6
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            slow = asyncio.create_task(client.get('/api/v1/public/x'))
            await asyncio.sleep(0.1)
            health = await client.get('/health')
            return health.status_code, (await slow).status_code

    assert asyncio.run(both()) == (200, 200)


def test_storefront_and_admin_have_separate_places():
    guard = LoadShedding(lambda *a: None, limits={'/api/v1/public/': 12, '': 6}, queue=1, wait=1)  # type: ignore[arg-type]
    names = {path: getattr(guard.bucket(path), 'name', None)
             for path in ('/api/v1/public/products/x', '/api/v1/admin/products', '/ready')}
    assert names == {'/api/v1/public/products/x': '/api/v1/public/', '/api/v1/admin/products': 'other',
                     '/ready': 'other'}


def test_the_api_takes_no_more_requests_than_connections(client):
    # Otherwise the lock of 12.11.2026 is possible again.
    assert settings.api_public_concurrency + settings.api_other_concurrency <= settings.db_pool_size + settings.db_max_overflow
    assert client.get('/health').status_code == 200
    response = client.get('/api/v1/public/site')
    assert response.status_code == 200
