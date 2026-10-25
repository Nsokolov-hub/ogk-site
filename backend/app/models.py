"""Import every ORM module so Base.metadata knows all tables (Alembic, tests and the worker)."""

import app.catalog.models  # noqa: F401
import app.outbox.models  # noqa: F401
import app.requests.models  # noqa: F401
import app.subscriptions.models  # noqa: F401
