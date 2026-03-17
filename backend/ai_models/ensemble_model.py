"""Weighted ensemble of CNN, VGG16, VGG19, and ResNet101 classifiers.

The pipeline mirrors the spec:
    MRI → YOLO detection → Region crop → 4× classifiers → Weighted average
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import torch

from backend.ai_models.cnn_classifier import (
    CLASS_NAMES,
    CNNClassifier,
    ResNet101Classifier,
    VGG16Classifier,
    VGG19Classifier,
)
from backend.ai_models.preprocessing import (
    classifier_transform,
    crop_region,
    load_mri_from_bytes,
)
from backend.ai_models.yolo_detector import YOLODetector
from backend.utils.logger import get_logger

if TYPE_CHECKING:
    from backend.ai_models.cnn_classifier import BaseClassifier
    from backend.ai_models.yolo_detector import Detection

logger = get_logger(__name__)

# Default ensemble weights (can be overridden via env)
DEFAULT_WEIGHTS: dict[str, float] = {
    "cnn": float(os.getenv("ENSEMBLE_W_CNN", "0.15")),
    "vgg16": float(os.getenv("ENSEMBLE_W_VGG16", "0.25")),
    "vgg19": float(os.getenv("ENSEMBLE_W_VGG19", "0.25")),
    "resnet101": float(os.getenv("ENSEMBLE_W_RESNET101", "0.35")),
}


@dataclass
class EnsemblePrediction:
    """Full result of the ensemble pipeline."""

    tumor_type: str
    confidence: float
    class_probabilities: dict[str, float]
    bbox: tuple[int, int, int, int] | None
    detection_confidence: float | None
    individual_predictions: dict[str, dict[str, float]]
    processing_time_ms: float
    location_estimate: str = ""
    size_estimate: str = ""


@dataclass
class EnsembleModel:
    """Orchestrates the full AI pipeline: YOLO → crop → classify → ensemble."""

    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    _detector: YOLODetector = field(default_factory=YOLODetector)
    _classifiers: dict[str, BaseClassifier] = field(default_factory=dict)

    def load_all(self) -> None:
        """Load every model in the pipeline."""
        self._detector.load()

        self._classifiers = {
            "cnn": CNNClassifier(),
            "vgg16": VGG16Classifier(),
            "vgg19": VGG19Classifier(),
            "resnet101": ResNet101Classifier(),
        }
        for clf in self._classifiers.values():
            clf.load()

        logger.info("ensemble_loaded", classifiers=list(self._classifiers.keys()))

    # ------------------------------------------------------------------
    # Main inference entry point
    # ------------------------------------------------------------------

    def predict(self, image_bytes: bytes) -> EnsemblePrediction:
        """Execute the full pipeline on raw image bytes.

        Flow:
            1. Decode image
            2. YOLO detection → best bounding box
            3. Crop detected region (or use full image if no detection)
            4. Run each classifier on the cropped region
            5. Weighted-average the probability vectors
            6. Return structured result
        """
        start = time.perf_counter()

        # 1. Decode
        image = load_mri_from_bytes(image_bytes)
        h, w = image.shape[:2]

        # 2. Detect
        detections = self._detector.detect(image)
        best: Detection | None = detections[0] if detections else None

        # 3. Crop
        if best is not None:
            cropped = crop_region(image, best.bbox)
            bbox = best.bbox
            det_conf = best.confidence
        else:
            # No detection — feed the full image to classifiers
            import cv2

            cropped = cv2.resize(image, (224, 224))
            bbox = None
            det_conf = None

        # 4. Classify with each backbone
        tensor = classifier_transform(cropped).unsqueeze(0)
        individual: dict[str, dict[str, float]] = {}
        prob_matrix: list[list[float]] = []

        for name, clf in self._classifiers.items():
            _, _, probs = clf.predict(tensor)
            individual[name] = {c: round(p, 4) for c, p in zip(CLASS_NAMES, probs)}
            prob_matrix.append(probs)

        # 5. Weighted ensemble
        weight_vec = np.array(
            [self.weights.get(n, 0.25) for n in self._classifiers]
        )
        weight_vec = weight_vec / weight_vec.sum()  # normalise

        prob_arr = np.array(prob_matrix)  # (4, num_classes)
        ensemble_probs = (weight_vec[:, None] * prob_arr).sum(axis=0)
        best_idx = int(ensemble_probs.argmax())
        confidence = float(ensemble_probs[best_idx])
        tumor_type = CLASS_NAMES[best_idx]

        # 6. Location / size heuristics
        location_estimate = ""
        size_estimate = ""
        if bbox is not None:
            cx = (bbox[0] + bbox[2]) / 2 / w
            cy = (bbox[1] + bbox[3]) / 2 / h
            location_estimate = _estimate_location(cx, cy)
            bw = bbox[2] - bbox[0]
            bh = bbox[3] - bbox[1]
            size_estimate = f"{max(bw, bh) * 0.1:.1f} cm (estimated)"

        elapsed = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "ensemble_prediction",
            tumor_type=tumor_type,
            confidence=round(confidence, 4),
            processing_time_ms=elapsed,
        )

        return EnsemblePrediction(
            tumor_type=tumor_type,
            confidence=round(confidence, 4),
            class_probabilities={
                c: round(float(p), 4) for c, p in zip(CLASS_NAMES, ensemble_probs)
            },
            bbox=bbox,
            detection_confidence=det_conf,
            individual_predictions=individual,
            processing_time_ms=elapsed,
            location_estimate=location_estimate,
            size_estimate=size_estimate,
        )

    def get_classifier(self, name: str) -> BaseClassifier:
        """Access a specific classifier (needed by Grad-CAM)."""
        return self._classifiers[name]


def _estimate_location(cx: float, cy: float) -> str:
    """Map normalised center coordinates to an anatomical description."""
    lr = "Left" if cx < 0.45 else ("Right" if cx > 0.55 else "Central")
    if cy < 0.35:
        ap = "frontal"
    elif cy < 0.65:
        ap = "parietal/temporal"
    else:
        ap = "occipital"
    return f"{lr} {ap} region"
