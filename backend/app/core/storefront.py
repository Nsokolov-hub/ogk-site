"""The storefront's cached API answers (Next Data Cache, 2–5 minutes): the API drops them after a change.

``POST {WEB_URL}/api/revalidate/`` with the tags of the changed pages; ``catalog`` covers the tree, listings,
suggestions and brand pages. Without WEB_URL or REVALIDATE_SECRET pages simply wait for their cache time.
"""

import logging

import httpx

from app.core.config import settings
from app.core.logs import event

logger = logging.getLogger('site.storefront')
MAX_TAGS = 1000


def revalidate(tags: list[str]) -> bool:
    if not (settings.web_url and settings.revalidate_secret) or not tags or len(tags) > MAX_TAGS:
        return False
    try:
        # The trailing slash: the storefront has trailingSlash on and answers 308 to the address without it.
        response = httpx.post(f'{settings.web_url.rstrip("/")}/api/revalidate/', timeout=5.0,
                              headers={'X-Revalidate-Secret': settings.revalidate_secret}, json={'tags': tags})
    except httpx.HTTPError as exc:
        event(logger, 'revalidate_failed', logging.WARNING, error=str(exc)[:200])
        return False
    if response.status_code != 200:
        event(logger, 'revalidate_failed', logging.WARNING, status=response.status_code)
        return False
    return True


def revalidate_catalog() -> bool:
    """After a command changed the catalog as a whole: seed, import, recategorize, rollback, settings."""
    return revalidate(['catalog'])
