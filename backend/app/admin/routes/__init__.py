"""The admin contour of the API: /api/v1/admin/* (TZ 12.2) — session, CSRF, roles, the journal of changes.

Caddy serves it on ADMIN_DOMAIN only; the public site answers 404 there (deploy/caddy/common.caddy).
"""

from fastapi import APIRouter

from app.admin.routes import (
    access,
    catalog,
    content,
    dictionaries,
    imports,
    journal,
    products,
    queues,
    requests,
    seo,
    site,
)

router = APIRouter(prefix='/admin', include_in_schema=False)
for module in (access, content, catalog, products, seo, requests, imports, queues, dictionaries, site, journal):
    router.include_router(module.router)
