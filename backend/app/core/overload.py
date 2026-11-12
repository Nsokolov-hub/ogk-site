"""Overload protection of the API (incident of 12.11.2026).

The endpoints are synchronous: each runs in a thread of the shared pool (40 threads) and holds a database connection
(10 + 10 in the pool) until FastAPI has built its response — and building the response of a synchronous endpoint
needs a thread again. When more requests than connections arrive at once, every thread waits for a connection while
the requests holding the connections wait for a thread: nothing moves until the pool's timeout fails the waiters.
On 12.11.2026 a burst of about 40 requests after a restart did that; the queue then grew to minutes and every page of
the storefront got a 500.

So the API takes at most as many requests at a time as it has connections, in two groups: the storefront and its
visitors (/api/v1/public/), and everything else (the admin panel, the CRM, /ready) — a flood of the first never
locks out the second. A request waits for a place a few seconds at most; when the queue is full or the wait is over,
it gets 503 with Retry-After at once instead of hanging.
"""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from app.core.logs import event

logger = logging.getLogger('site.api')

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

MESSAGE = 'Сайт сейчас перегружен. Повторите через несколько секунд или позвоните нам: +7 495 234 28 63'


class Bucket:
    """Places for requests of one group; waiting ones queue in arrival order."""

    def __init__(self, name: str, limit: int) -> None:
        self.name = name
        self.limit = limit
        self.waiting = 0
        self.running = 0
        self.shed = 0
        self.logged_at = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._places = asyncio.Semaphore(limit)

    def _bound(self) -> asyncio.Semaphore:
        # The API runs one event loop; tests start one per client, and a semaphore belongs to the loop it waited in.
        loop = asyncio.get_running_loop()
        if self._loop is not loop:
            self._loop, self._places, self.waiting, self.running = loop, asyncio.Semaphore(self.limit), 0, 0
        return self._places

    async def enter(self, queue: int, wait: float) -> bool:
        places = self._bound()
        if places.locked():
            if self.waiting >= queue:
                return False
            self.waiting += 1
            try:
                async with asyncio.timeout(wait):
                    await places.acquire()
            except TimeoutError:
                return False
            finally:
                self.waiting -= 1
        else:
            await places.acquire()
        self.running += 1
        return True

    def leave(self) -> None:
        self.running -= 1
        self._places.release()


class LoadShedding:
    """ASGI middleware: ``limits`` maps a path prefix to the requests it may run at once ('' — every other path);
    ``queue`` requests of a group may wait, each ``wait`` seconds at most; ``exempt`` paths (no database) pass."""

    def __init__(self, app: ASGIApp, *, limits: dict[str, int], queue: int, wait: float,
                 exempt: tuple[str, ...] = ('/health',)) -> None:
        self.app = app
        self.queue = queue
        self.wait = wait
        self.exempt = exempt
        self.buckets = sorted(((prefix, Bucket(prefix or 'other', limit)) for prefix, limit in limits.items()),
                              key=lambda item: -len(item[0]))

    def bucket(self, path: str) -> Bucket | None:
        return next((bucket for prefix, bucket in self.buckets if path.startswith(prefix)), None)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        bucket = self.bucket(scope['path']) if scope['type'] == 'http' and scope['path'] not in self.exempt else None
        if bucket is None:
            await self.app(scope, receive, send)
            return
        if not await bucket.enter(self.queue, self.wait):
            scope['overloaded'] = True
            self._report(bucket)
            await self._reject(scope, send)
            return
        try:
            await self.app(scope, receive, send)
        finally:
            bucket.leave()

    def _report(self, bucket: Bucket) -> None:
        # One line a second at most: during a flood every refused request is also in the http_request line (503).
        bucket.shed += 1
        now = time.monotonic()
        if now - bucket.logged_at >= 1:
            event(logger, 'overload_shed', logging.WARNING, group=bucket.name, shed=bucket.shed, running=bucket.running,
                  waiting=bucket.waiting, limit=bucket.limit)
            bucket.logged_at, bucket.shed = now, 0

    async def _reject(self, scope: Scope, send: Send) -> None:
        request_id = (scope.get('state') or {}).get('request_id')
        body = json.dumps({'code': 'OVERLOADED', 'message': MESSAGE, 'field': None, 'requestId': request_id},
                          ensure_ascii=False).encode()
        await send({'type': 'http.response.start', 'status': 503, 'headers': [
            (b'content-type', b'application/json'), (b'content-length', str(len(body)).encode()),
            (b'retry-after', str(max(1, round(self.wait))).encode()), (b'cache-control', b'no-store')]})
        await send({'type': 'http.response.body', 'body': body})
