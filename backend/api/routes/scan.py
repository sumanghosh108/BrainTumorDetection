"""Scan endpoints — upload, predict, retrieve results, patient history."""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.db import get_db
from backend.database.models import Patient, Prediction, Report, Scan
from backend.schemas.scan import (
    FullResultResponse,
    PredictionResponse,
    PredictionResult,
    RadiologyReport,
    ScanHistory,
    ScanStatus,
    TumorType,
    UploadResponse,
)
from backend.services.auth_service import get_current_user
from backend.services.s3_service import upload_gradcam, upload_mri
from backend.utils.audit_log import AuditEventType, audit_event
from backend.utils.logger import get_logger

if TYPE_CHECKING:
    from backend.ai_models.ensemble_model import EnsembleModel

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["scan"])

ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "application/dicom",
    "application/octet-stream",
}


def _get_ensemble(request: Request) -> EnsembleModel:
    """Retrieve the ensemble model stored on app state during startup."""
    ensemble: EnsembleModel | None = getattr(request.app.state, "ensemble", None)
    if ensemble is None:
        raise HTTPException(status_code=503, detail="AI models not loaded")
    return ensemble


# ---------------------------------------------------------------------------
# POST /scan/upload
# ---------------------------------------------------------------------------


@router.post("/scan/upload", response_model=UploadResponse, status_code=201)
async def upload_scan(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> UploadResponse:
    """Upload an MRI scan to S3 and persist metadata."""
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {file.content_type}",
        )

    # Resolve or create patient from Firebase uid
    patient = (
        await db.execute(select(Patient).where(Patient.firebase_uid == user_id))
    ).scalar_one_or_none()

    if patient is None:
        patient = Patient(firebase_uid=user_id)
        db.add(patient)
        await db.flush()

    scan_id = uuid.uuid4()
    s3_url = await upload_mri(file, scan_id)
    s3_key = s3_url.split(".amazonaws.com/", 1)[-1]

    scan = Scan(
        id=scan_id,
        patient_id=patient.id,
        s3_key=s3_key,
        s3_url=s3_url,
        status=ScanStatus.UPLOADED,
    )
    db.add(scan)
    await db.flush()

    await audit_event(
        db,
        AuditEventType.SCAN_UPLOADED,
        user_id=patient.id,
        scan_id=scan_id,
        metadata={"filename": file.filename, "content_type": file.content_type},
    )

    return UploadResponse(
        scan_id=scan_id,
        s3_url=s3_url,
        status=ScanStatus.UPLOADED,
        uploaded_at=scan.uploaded_at,
    )


# ---------------------------------------------------------------------------
# POST /scan/{id}/predict
# ---------------------------------------------------------------------------


@router.post("/scan/{scan_id}/predict", response_model=PredictionResponse)
async def predict_scan(
    scan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> PredictionResponse:
    """Run the full AI pipeline on an uploaded scan."""
    scan = (
        await db.execute(select(Scan).where(Scan.id == scan_id))
    ).scalar_one_or_none()

    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.prediction is not None:
        raise HTTPException(status_code=409, detail="Prediction already exists for this scan")

    ensemble = _get_ensemble(request)

    scan.status = ScanStatus.PROCESSING
    await db.flush()

    await audit_event(db, AuditEventType.PREDICTION_STARTED, scan_id=scan_id)

    # ------------------------------------------------------------------
    # Fetch the image bytes from S3 and run the ensemble pipeline
    # ------------------------------------------------------------------
    from backend.services.s3_service import download_scan_bytes

    image_bytes = await download_scan_bytes(scan.s3_key)

    # Run CPU/GPU-bound inference in a thread to avoid blocking the event loop
    result = await asyncio.to_thread(ensemble.predict, image_bytes)

    # ------------------------------------------------------------------
    # Generate Grad-CAM heatmap and upload to S3
    # ------------------------------------------------------------------
    gradcam_url: str | None = None
    try:
        from backend.ai_models.preprocessing import load_mri_from_bytes, crop_region
        from backend.explainability.gradcam import generate_gradcam, gradcam_to_png_bytes
        from backend.ai_models.cnn_classifier import CLASS_NAMES

        image = load_mri_from_bytes(image_bytes)
        if result.bbox is not None:
            region = crop_region(image, result.bbox)
        else:
            import cv2
            region = cv2.resize(image, (224, 224))

        # Use the highest-weighted classifier for the explanation
        best_clf = ensemble.get_classifier("resnet101")
        target_idx = CLASS_NAMES.index(result.tumor_type)
        overlay = generate_gradcam(best_clf, region, target_class_idx=target_idx)
        png_bytes = gradcam_to_png_bytes(overlay)
        gradcam_url = await upload_gradcam(png_bytes, scan_id)
    except Exception:
        logger.exception("gradcam_generation_failed", scan_id=str(scan_id))

    # ------------------------------------------------------------------
    # Persist prediction + report
    # ------------------------------------------------------------------
    tumor_type = TumorType(result.tumor_type)

    prediction = Prediction(
        scan_id=scan_id,
        tumor_type=tumor_type.value,
        confidence=result.confidence,
        location=result.location_estimate,
        size_estimate=result.size_estimate,
        gradcam_url=gradcam_url,
        processing_time_ms=result.processing_time_ms,
    )
    db.add(prediction)

    scan.status = ScanStatus.COMPLETED
    await db.flush()

    # Auto-generate structured report
    from backend.report.radiology_report import generate_report

    report_data = generate_report(
        prediction=result,
        patient_id=scan.patient_id,
        scan_id=scan_id,
        gradcam_url=gradcam_url or "",
    )

    report = Report(
        scan_id=scan_id,
        patient_id=scan.patient_id,
        recommendation=report_data.recommendation,
    )
    db.add(report)
    await db.flush()

    await audit_event(
        db,
        AuditEventType.PREDICTION_COMPLETED,
        scan_id=scan_id,
        metadata={
            "tumor_type": tumor_type.value,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms,
        },
    )
    await audit_event(db, AuditEventType.REPORT_GENERATED, scan_id=scan_id)

    return PredictionResponse(
        scan_id=scan_id,
        status=ScanStatus.COMPLETED,
        prediction=PredictionResult(
            tumor_type=tumor_type,
            confidence=result.confidence,
            location=result.location_estimate,
            size_estimate=result.size_estimate,
        ),
        gradcam_url=gradcam_url,
        processing_time_ms=result.processing_time_ms,
        predicted_at=prediction.predicted_at,
    )


# ---------------------------------------------------------------------------
# GET /scan/{id}/result
# ---------------------------------------------------------------------------


@router.get("/scan/{scan_id}/result", response_model=FullResultResponse)
async def get_scan_result(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> FullResultResponse:
    """Retrieve the full result (scan + prediction + report) for a scan."""
    scan = (
        await db.execute(select(Scan).where(Scan.id == scan_id))
    ).scalar_one_or_none()

    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    prediction_schema: PredictionResult | None = None
    if scan.prediction:
        prediction_schema = PredictionResult(
            tumor_type=TumorType(scan.prediction.tumor_type),
            confidence=scan.prediction.confidence,
            location=scan.prediction.location,
            size_estimate=scan.prediction.size_estimate,
        )

    report_schema: RadiologyReport | None = None
    if scan.report and scan.prediction:
        report_schema = RadiologyReport(
            report_id=scan.report.id,
            patient_id=scan.report.patient_id,
            scan_id=scan_id,
            scan_date=scan.uploaded_at,
            tumor_type=TumorType(scan.prediction.tumor_type),
            confidence=scan.prediction.confidence,
            location=scan.prediction.location,
            size_estimate=scan.prediction.size_estimate,
            gradcam_url=scan.prediction.gradcam_url,
            recommendation=scan.report.recommendation,
            generated_at=scan.report.generated_at,
        )

    return FullResultResponse(
        scan_id=scan.id,
        patient_id=scan.patient_id,
        s3_url=scan.s3_url,
        status=ScanStatus(scan.status),
        prediction=prediction_schema,
        report=report_schema,
        uploaded_at=scan.uploaded_at,
        completed_at=scan.prediction.predicted_at if scan.prediction else None,
    )


# ---------------------------------------------------------------------------
# GET /patient/{id}/history
# ---------------------------------------------------------------------------


@router.get("/patient/{patient_id}/history", response_model=list[ScanHistory])
async def get_patient_history(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> list[ScanHistory]:
    """Return the scan history for a patient, most recent first."""
    result = await db.execute(
        select(Scan)
        .where(Scan.patient_id == patient_id)
        .order_by(Scan.uploaded_at.desc())
    )
    scans = result.scalars().all()

    return [
        ScanHistory(
            scan_id=s.id,
            scan_date=s.uploaded_at,
            tumor_type=TumorType(s.prediction.tumor_type) if s.prediction else None,
            confidence=s.prediction.confidence if s.prediction else None,
            status=ScanStatus(s.status),
            s3_url=s.s3_url,
        )
        for s in scans
    ]
