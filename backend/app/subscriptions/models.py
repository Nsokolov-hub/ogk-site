"""Subscribers of the mailing (TZ 11.2 «Feedback», NFR-07): an address with both consents, its source and the way out.

A mailing goes only to an active subscriber with a separate consent to advertising (38-FZ art. 18); every letter
carries the unsubscribe link. The CRM gets every subscriber as a contact for mailings.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Entity, utcnow


class Subscriber(Entity):
    __tablename__ = 'subscribers'
    __table_args__ = (
        CheckConstraint("status IN ('active', 'unsubscribed')"),
        CheckConstraint("lang IN ('ru', 'en')"),
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    lang: Mapped[str] = mapped_column(String(2), default='ru')
    status: Mapped[str] = mapped_column(String(20), default='active', index=True)
    source: Mapped[str | None] = mapped_column(String(40))
    page_url: Mapped[str | None] = mapped_column(String(2000))
    # Evidence of both consents (152-FZ and 38-FZ): when and from which address they were given.
    personal_data_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    marketing_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    unsubscribe_token: Mapped[str] = mapped_column(String(64), unique=True)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    crm_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
