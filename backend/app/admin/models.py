"""The admin panel (TZ 13): staff accounts and sessions, the journal of changes, page contents, drafts, redirects,
SEO landings and the demand counters of the «обогатить» queue.

Staff accounts are separate from customers (TZ 8) and from the CRM: the site has no customer accounts in Release 1.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.catalog.models import Doc
from app.core.db import Base, Entity, utcnow

ROLES = ('admin', 'content', 'catalog', 'viewer')
PAGE_KINDS = ('home', 'service', 'solution', 'article', 'author', 'trust')


class StaffUser(Entity):
    __tablename__ = 'staff_users'
    __table_args__ = (CheckConstraint("role IN ('admin', 'content', 'catalog', 'viewer')"),)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # The TOTP secret is kept encrypted with SECRET_KEY (ADM-01: TOTP for administrators).
    totp_secret: Mapped[str | None] = mapped_column(Text)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StaffSession(Entity):
    __tablename__ = 'staff_sessions'
    user_id: Mapped[str] = mapped_column(ForeignKey('staff_users.id', ondelete='CASCADE'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditEntry(Base):
    """Every change made in the admin panel, with the state before and after it: the history of a page or a card
    and the way back to any of its versions (ADM-01)."""

    __tablename__ = 'audit_entries'
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True,
                                    autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_name: Mapped[str] = mapped_column(String(200))
    entity: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(200), index=True)
    action: Mapped[str] = mapped_column(String(30))
    summary: Mapped[str] = mapped_column(String(300), default='')
    before: Mapped[Any] = mapped_column(JSON, nullable=True)
    after: Mapped[Any] = mapped_column(JSON, nullable=True)


class ContentPage(Entity):
    """A page of the site: the home page, services, solutions, articles, authors, trust pages (ADM-02).

    ``content`` is ``{"ru": {...}, "en": {...}}`` in the shape the storefront renders (web src/types/content.ts);
    an English version exists only when it is translated (EN-05).
    """

    __tablename__ = 'content_pages'
    __table_args__ = (UniqueConstraint('kind', 'slug'),
                      CheckConstraint("status IN ('published', 'hidden')"))
    kind: Mapped[str] = mapped_column(String(20), index=True)
    slug: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[dict[str, Any]] = mapped_column(Doc, default=dict)
    status: Mapped[str] = mapped_column(String(20), default='published')
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Draft(Entity):
    """Unpublished edits of a page, category, brand, substance or landing: previewed on the storefront by a signed
    link, published by hand or at ``publish_at`` by the worker (ADM-02)."""

    __tablename__ = 'drafts'
    __table_args__ = (UniqueConstraint('entity', 'entity_id'),)
    entity: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(36))
    data: Mapped[dict[str, Any]] = mapped_column(Doc, default=dict)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    author_id: Mapped[str | None] = mapped_column(String(36))
    author_name: Mapped[str] = mapped_column(String(200), default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Redirect(Entity):
    """A redirect from an old address (ADM-07): 301 for moved pages, 302 for temporary ones (URL-11)."""

    __tablename__ = 'redirects'
    __table_args__ = (CheckConstraint('code IN (301, 302)'),)
    source: Mapped[str] = mapped_column(String(400), unique=True)
    target: Mapped[str] = mapped_column(String(500))
    code: Mapped[int] = mapped_column(Integer, default=301)
    note: Mapped[str | None] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SeoLanding(Entity):
    """An SEO landing cut from the filters of a category (URL-07): its own address, H1, Title and text, fixed
    filters; indexed with at least 3 products."""

    __tablename__ = 'seo_landings'
    __table_args__ = (UniqueConstraint('category_path', 'slug'),
                      CheckConstraint("status IN ('published', 'hidden')"))
    category_path: Mapped[str] = mapped_column(String(400), index=True)
    slug: Mapped[str] = mapped_column(String(120))
    filters: Mapped[dict[str, list[str]]] = mapped_column(JSON, default=dict)
    content: Mapped[dict[str, Any]] = mapped_column(Doc, default=dict)
    status: Mapped[str] = mapped_column(String(20), default='published')
    position: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProductDemand(Base):
    """Views of a card and requests with it per day: the order of the «обогатить» queue (TZ 5.6)."""

    __tablename__ = 'product_demand'
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    requests: Mapped[int] = mapped_column(Integer, default=0)


class ImportUpload(Entity):
    """A file loaded in the import wizard (ADM-04): kept until its batch has run."""

    __tablename__ = 'import_uploads'
    file_name: Mapped[str] = mapped_column(String(300))
    storage_key: Mapped[str] = mapped_column(String(200), unique=True)
    size: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    header: Mapped[list[str]] = mapped_column(JSON, default=list)
    sample: Mapped[list[list[str | None]]] = mapped_column(JSON, default=list)
    author_name: Mapped[str] = mapped_column(String(200), default='')
    # queued → running → done | failed; the batches it made are in import_batches with this upload's name.
    status: Mapped[str] = mapped_column(String(20), default='uploaded')
    source: Mapped[str | None] = mapped_column(String(60))
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    batch_id: Mapped[str | None] = mapped_column(String(36))
    error: Mapped[str | None] = mapped_column(Text)
