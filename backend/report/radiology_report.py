"""Structured radiology report generator.

Converts an ``EnsemblePrediction`` into a ``RadiologyReportData`` object
that can be serialised to JSON, stored in the DB, and rendered by the
frontend report panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from backend.ai_models.ensemble_model import EnsemblePrediction

# ---------------------------------------------------------------------------
# Recommendation templates (keyed by tumor_type)
# ---------------------------------------------------------------------------

_RECOMMENDATIONS: dict[str, str] = {
    "glioma": (
        "Findings are consistent with a glioma. Urgent referral to neuro-oncology "
        "is recommended. Consider contrast-enhanced MRI with perfusion imaging for "
        "grading. Discuss multidisciplinary tumour board review and biopsy planning."
    ),
    "meningioma": (
        "Imaging features suggest a meningioma. Neurosurgical consultation is "
        "recommended. If asymptomatic, serial imaging at 6-month intervals may be "
        "appropriate. Evaluate for surgical candidacy based on size and location."
    ),
    "pituitary": (
        "Findings are suggestive of a pituitary adenoma. Endocrinology referral "
        "for hormonal workup is advised. Obtain dedicated sellar MRI with thin "
        "coronal and sagittal cuts. Visual field testing is recommended."
    ),
    "no_tumor": (
        "No intracranial mass detected. If clinical suspicion persists, consider "
        "repeat imaging in 6–12 months or advanced sequences (FLAIR, DWI). "
        "Correlation with clinical history is advised."
    ),
}


@dataclass
class RadiologyReportData:
    """Complete structured radiology report ready for persistence."""

    report_id: UUID = field(default_factory=uuid4)
    patient_id: UUID = field(default_factory=uuid4)
    scan_id: UUID = field(default_factory=uuid4)
    scan_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tumor_type: str = "no_tumor"
    confidence: float = 0.0
    class_probabilities: dict[str, float] = field(default_factory=dict)
    location: str = ""
    size_estimate: str = ""
    gradcam_url: str = ""
    recommendation: str = ""
    individual_model_results: dict[str, dict[str, float]] = field(default_factory=dict)
    processing_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "report_id": str(self.report_id),
            "patient_id": str(self.patient_id),
            "scan_id": str(self.scan_id),
            "scan_date": self.scan_date.isoformat(),
            "tumor_type": self.tumor_type,
            "confidence": self.confidence,
            "class_probabilities": self.class_probabilities,
            "location": self.location,
            "size_estimate": self.size_estimate,
            "gradcam_url": self.gradcam_url,
            "recommendation": self.recommendation,
            "individual_model_results": self.individual_model_results,
            "processing_time_ms": self.processing_time_ms,
        }


def generate_report(
    prediction: EnsemblePrediction,
    patient_id: UUID,
    scan_id: UUID,
    gradcam_url: str = "",
) -> RadiologyReportData:
    """Build a ``RadiologyReportData`` from an ensemble prediction.

    Args:
        prediction: Output of ``EnsembleModel.predict()``.
        patient_id: Owning patient UUID.
        scan_id: Associated scan UUID.
        gradcam_url: Pre-signed or public URL to the Grad-CAM overlay image.

    Returns:
        Fully populated ``RadiologyReportData``.
    """
    recommendation = _RECOMMENDATIONS.get(
        prediction.tumor_type,
        "Please consult a radiologist for further evaluation.",
    )

    # Append confidence-aware addendum
    if prediction.confidence < 0.70 and prediction.tumor_type != "no_tumor":
        recommendation += (
            "\n\nNote: Model confidence is below 70 %. Results should be "
            "interpreted with caution and corroborated with additional imaging."
        )

    return RadiologyReportData(
        patient_id=patient_id,
        scan_id=scan_id,
        scan_date=datetime.now(timezone.utc),
        tumor_type=prediction.tumor_type,
        confidence=prediction.confidence,
        class_probabilities=prediction.class_probabilities,
        location=prediction.location_estimate,
        size_estimate=prediction.size_estimate,
        gradcam_url=gradcam_url,
        recommendation=recommendation,
        individual_model_results=prediction.individual_predictions,
        processing_time_ms=prediction.processing_time_ms,
    )
