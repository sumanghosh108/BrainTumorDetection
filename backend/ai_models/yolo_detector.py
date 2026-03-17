"""YOLOv8 brain tumor detection wrapper."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ultralytics import YOLO

from backend.utils.logger import get_logger

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

logger = get_logger(__name__)

YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "weights/yolov8_brain_tumor.pt")
YOLO_CONF_THRESHOLD = float(os.getenv("YOLO_CONF_THRESHOLD", "0.25"))


@dataclass
class Detection:
    """A single bounding-box detection."""

    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    class_id: int
    class_name: str


class YOLODetector:
    """Wrapper around a YOLOv8 model trained for brain tumor localisation."""

    def __init__(self, model_path: str = YOLO_MODEL_PATH) -> None:
        self._model_path = model_path
        self._model: YOLO | None = None

    def load(self) -> None:
        """Load the YOLO model weights from disk."""
        if not os.path.isfile(self._model_path):
            logger.warning(
                "yolo_weights_missing",
                path=self._model_path,
                hint="Place your trained YOLOv8 .pt file at this path.",
            )
            return
        self._model = YOLO(self._model_path)
        logger.info("yolo_model_loaded", path=self._model_path)

    def detect(
        self,
        image: NDArray[np.uint8],
        conf: float = YOLO_CONF_THRESHOLD,
    ) -> list[Detection]:
        """Run inference and return detected bounding boxes.

        Args:
            image: RGB numpy array (any size — YOLO resizes internally).
            conf: Minimum confidence threshold.

        Returns:
            List of ``Detection`` objects sorted by descending confidence.
        """
        if self._model is None:
            logger.warning("yolo_model_not_loaded — returning empty detections")
            return []

        results = self._model.predict(source=image, conf=conf, verbose=False)
        detections: list[Detection] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(
                    Detection(
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        confidence=float(box.conf[0]),
                        class_id=int(box.cls[0]),
                        class_name=result.names[int(box.cls[0])],
                    )
                )

        detections.sort(key=lambda d: d.confidence, reverse=True)
        logger.info("yolo_detections", count=len(detections))
        return detections
