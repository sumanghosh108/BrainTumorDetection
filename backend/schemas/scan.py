"""Pydantic v2 schemas for scan-related API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class TumorType(StrEnum):
    GLIOMA = "glioma"
    MENINGIOMA = "meningioma"
    PITUITARY = "pituitary"
    NO_TUMOR = "no_tumor"


class ScanStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID
    s3_url: str
    status: ScanStatus = ScanStatus.UPLOADED
    uploaded_at: datetime


class PredictionResult(BaseModel):
    tumor_type: TumorType
    confidence: float = Field(..., ge=0.0, le=1.0)
    location: str | None = None
    size_estimate: str | None = None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID
    status: ScanStatus
    prediction: PredictionResult
    gradcam_url: str | None = None
    processing_time_ms: float
    predicted_at: datetime


class RadiologyReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: UUID
    patient_id: UUID
    scan_id: UUID
    scan_date: datetime
    tumor_type: TumorType
    confidence: float = Field(..., ge=0.0, le=1.0)
    location: str | None = None
    size_estimate: str | None = None
    gradcam_url: str | None = None
    recommendation: str
    generated_at: datetime


class FullResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID
    patient_id: UUID
    s3_url: str
    status: ScanStatus
    prediction: PredictionResult | None = None
    report: RadiologyReport | None = None
    uploaded_at: datetime
    completed_at: datetime | None = None


class ScanHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID
    scan_date: datetime
    tumor_type: TumorType | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    status: ScanStatus
    s3_url: str
