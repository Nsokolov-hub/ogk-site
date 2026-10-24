"""Import every ORM module so Base.metadata knows all tables (Alembic, tests and the worker)."""

import app.outbox.models  # noqa: F401
import app.requests.models  # noqa: F401
