"""Requests sent from the site's forms and the journal of their delivery to the CRM.

The site keeps the original request and the delivery journal only; the CRM is the master of clients and deals
(TZ 9.2). A request is written here before the customer gets an answer, so it is never lost (NFR-03).
"""

from datetime import date, datetime
from decimal import Decimal
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
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Entity, utcnow

# accepted → delivered; accepted → failed (a permanent CRM refusal or 24 hours of failures) → resent by hand.
REQUEST_STATUSES = ('accepted', 'delivered', 'failed')


class SiteRequest(Entity):
    __tablename__ = 'site_requests'
    __table_args__ = (
        CheckConstraint("status IN ('accepted', 'delivered', 'failed')"),
        CheckConstraint("kind IN ('product_rfq', 'one_click', 'service', 'general')"),
        CheckConstraint("lang IN ('ru', 'en')"),
    )
    # id is the site_request_id of contract F1 and the Idempotency-Key of every delivery attempt.
    number: Mapped[str] = mapped_column(String(40), unique=True)
    # Idempotency-Key of the browser: a double click or a network retry returns the same request.
    client_key: Mapped[str] = mapped_column(String(64), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(20))
    lang: Mapped[str] = mapped_column(String(2))
    form_type: Mapped[str | None] = mapped_column(String(40))
    page_url: Mapped[str | None] = mapped_column(String(2000))
    customer_name: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(250))
    inn: Mapped[str | None] = mapped_column(String(12))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(254))
    city: Mapped[str | None] = mapped_column(String(200))
    comment: Mapped[str | None] = mapped_column(Text)
    desired_date: Mapped[date | None] = mapped_column(Date)
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    # Evidence of the consent to personal data processing (152-FZ): when and from which address.
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    service: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    # The attribution block of contract F1, computed when the request arrived.
    attribution: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default='accepted', index=True)
    crm_id: Mapped[str | None] = mapped_column(String(36))
    crm_number: Mapped[str | None] = mapped_column(String(40))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_error: Mapped[str | None] = mapped_column(String(80))
    alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SiteRequestItem(Entity):
    __tablename__ = 'site_request_items'
    __table_args__ = (
        CheckConstraint('quantity > 0'),
        CheckConstraint("analogue IN ('none', 'allowed', 'requested')"),
    )
    request_id: Mapped[str] = mapped_column(ForeignKey('site_requests.id'), index=True)
    position: Mapped[int] = mapped_column(Integer)
    site_product_id: Mapped[str | None] = mapped_column(String(100))
    brand: Mapped[str | None] = mapped_column(String(200))
    catalog_number: Mapped[str | None] = mapped_column(String(150))
    cas: Mapped[str | None] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(500))
    packaging: Mapped[str | None] = mapped_column(String(200))
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    unit: Mapped[str] = mapped_column(String(20))
    analogue: Mapped[str] = mapped_column(String(20))
    custom_packaging: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str | None] = mapped_column(Text)
    page_url: Mapped[str | None] = mapped_column(String(2000))


class SiteRequestAttachment(Entity):
    __tablename__ = 'site_request_attachments'
    request_id: Mapped[str] = mapped_column(ForeignKey('site_requests.id'), index=True)
    file_name: Mapped[str] = mapped_column(String(250))
    media_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(200), unique=True)


class DeliveryAttempt(Entity):
    """The integration journal: every call to the CRM. KPI «100% delivered, ≤ 1 min» is counted from it."""

    __tablename__ = 'delivery_attempts'
    request_id: Mapped[str] = mapped_column(ForeignKey('site_requests.id'), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))
    status_code: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(80))
    duration_ms: Mapped[int] = mapped_column(Integer)


class NumberCounter(Base):
    __tablename__ = 'number_counters'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)


class RateEvent(Base):
    """One submission attempt per row, by a hash of the client address; old rows are pruned by the worker."""

    __tablename__ = 'rate_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
