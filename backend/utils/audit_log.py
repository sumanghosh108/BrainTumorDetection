"""Audit logging — writes events to the Supabase audit_logs table and stdout."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from backend.utils.logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("audit")


class AuditEventType(StrEnum):
    SCAN_UPLOADED = "SCAN_UPLOADED"
    PREDICTION_STARTED = "PREDICTION_STARTED"
    PREDICTION_COMPLETED = "PREDICTION_COMPLETED"
    REPORT_GENERATED = "REPORT_GENERATED"
    AUTH_LOGIN = "AUTH_LOGIN"
    AUTH_FAILURE = "AUTH_FAILURE"


async def audit_event(
    db: AsyncSession,
    event_type: AuditEventType,
    user_id: uuid.UUID | None = None,
    scan_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record an audit event to the database and emit a structured log line."""
    from backend.database.models import AuditLog

    entry = AuditLog(
        event_type=event_type.value,
        user_id=user_id,
        scan_id=scan_id,
        metadata_=metadata or {},
    )
    db.add(entry)
    await db.flush()

    logger.info(
        "audit_event",
        event_type=event_type.value,
        user_id=str(user_id) if user_id else None,
        scan_id=str(scan_id) if scan_id else None,
        metadata=metadata,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
