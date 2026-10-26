"""Events received from the CRM (flow F2): one row per event id, so a repeat gets the first answer back."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class CrmEvent(Base):
    __tablename__ = 'crm_events'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(60), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    # The answer given to the CRM: a repeat of the event gets it unchanged.
    answer: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
