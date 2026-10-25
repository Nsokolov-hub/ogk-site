"""Limits of the public API per visitor and minute (NFR-05), shared by every API process through Redis.

Without REDIS_URL (development, tests) or while Redis is down the counts stay in this process: a little more
lenient across processes, but a visitor is never refused because Redis is unavailable.
"""

import logging
import threading
import time
from collections import deque
from typing import Any

from app.core.config import settings
from app.core.logs import event

logger = logging.getLogger('site.ratelimit')


class RateLimiter:
    def __init__(self, scope: str) -> None:
        self.scope = scope
        self.hits: dict[str, deque[float]] = {}
        self.lock = threading.Lock()
        self.pruned = time.monotonic()
        self.redis_failed_at = 0.0

    def allow(self, key: str, per_minute: int) -> bool:
        client = redis_client()
        if client is not None and time.monotonic() - self.redis_failed_at > 30:
            try:
                return self._allow_redis(client, key, per_minute)
            except Exception as exc:  # any Redis trouble: count here for 30 seconds
                self.redis_failed_at = time.monotonic()
                event(logger, 'ratelimit_redis_unavailable', logging.WARNING, error=type(exc).__name__)
        return self._allow_memory(key, per_minute)

    def _allow_redis(self, client: Any, key: str, per_minute: int) -> bool:
        minute = int(time.time() // 60)
        name = f'rl:{self.scope}:{key}:{minute}'
        pipe = client.pipeline()
        pipe.incr(name)
        pipe.expire(name, 90)
        count = pipe.execute()[0]
        return int(count) <= per_minute

    def _allow_memory(self, key: str, per_minute: int) -> bool:
        now = time.monotonic()
        with self.lock:
            if now - self.pruned > 300:
                self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < 60}
                self.pruned = now
            window = self.hits.setdefault(key, deque())
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= per_minute:
                return False
            window.append(now)
            return True


_client: Any = None
_client_url = ''


def redis_client() -> Any:
    """One connection pool per process; None without REDIS_URL."""
    global _client, _client_url
    if not settings.redis_url:
        return None
    if _client is None or _client_url != settings.redis_url:
        import redis

        _client = redis.Redis.from_url(settings.redis_url, socket_timeout=0.3, socket_connect_timeout=0.3)
        _client_url = settings.redis_url
    return _client
