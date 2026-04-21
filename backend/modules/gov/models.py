"""
GOV Connector — SQLAlchemy models for ISDS datové schránky.

Design: poller stores NOTIFICATION metadata only (subject, sender, date).
Full message content (ZFO, attachments) downloaded ON DEMAND only.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    Index, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship
from backend.core.models.base import Base


class GovSchranka(Base):
    """Registered datová schránka — one per legal entity."""
    __tablename__ = "gov_schranka"

    ds_id = Column(String(7), primary_key=True)  # e.g. "redcvk5"
    name = Column(String(200), nullable=False)     # e.g. "LOGPACK, s.r.o."
    subject_type = Column(String(50))              # FO / PFO / PO / OVM
    active = Column(Boolean, default=True)
    credentials_ok = Column(Boolean, default=False)
    username = Column(String(20))
    password_expires_at = Column(DateTime)
    last_poll = Column(DateTime)
    last_poll_status = Column(String(50))          # ok / auth_failed / network_error
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    messages = relationship("GovMessage", back_populates="schranka")


class GovMessage(Base):
    """Message notification from ISDS — metadata only, no content stored by default."""
    __tablename__ = "gov_message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(20), unique=True, nullable=False)  # ISDS message ID
    ds_id = Column(String(7), ForeignKey("gov_schranka.ds_id"), nullable=False)
    direction = Column(String(10))  # received / sent

    subject = Column(String(500))
    sender_name = Column(String(200))
    sender_ds_id = Column(String(7))
    sender_org_unit = Column(String(200))

    received_at = Column(DateTime)
    accepted_at = Column(DateTime)      # when legally accepted (delivery confirmation)
    status_text = Column(String(50))    # delivered / read / etc.

    # Deadline detection from subject
    is_urgent = Column(Boolean, default=False)
    detected_deadline = Column(DateTime)  # e.g. KH deadline parsed from subject
    deadline_type = Column(String(50))    # KH / DPH / odpoved / etc.

    # On-demand download tracking
    downloaded = Column(Boolean, default=False)
    downloaded_at = Column(DateTime)
    zfo_path = Column(String(500))  # path to downloaded ZFO file
    attachment_count = Column(Integer)

    # Alert tracking
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())

    schranka = relationship("GovSchranka", back_populates="messages")

    __table_args__ = (
        Index("idx_gov_msg_ds_received", "ds_id", "received_at"),
        Index("idx_gov_msg_deadline", "detected_deadline"),
        Index("idx_gov_msg_unread", "alert_sent", "downloaded"),
    )


class GovAttachment(Base):
    """Attachment metadata — populated only after on-demand download."""
    __tablename__ = "gov_attachment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("gov_message.id"), nullable=False)
    filename = Column(String(300), nullable=False)
    mime_type = Column(String(100))
    size_bytes = Column(Integer)
    local_path = Column(String(500))
    sha256 = Column(String(64))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_gov_attach_msg", "message_id"),
    )
