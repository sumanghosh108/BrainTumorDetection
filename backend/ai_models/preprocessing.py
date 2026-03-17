"""MRI image preprocessing utilities for the detection/classification pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np
from torchvision import transforms

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Standard input size for classifiers (VGG / ResNet expect 224×224)
CLASSIFIER_INPUT_SIZE = (224, 224)

# Normalisation stats (ImageNet — used because classifiers are pretrained on it)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Transform pipeline for classification models
classifier_transform = transforms.Compose(
    [
        transforms.ToPILImage(),
        transforms.Resize(CLASSIFIER_INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ]
)

# YOLOv8 expects 640×640 RGB by default
YOLO_INPUT_SIZE = (640, 640)


def load_mri_image(path: str) -> NDArray[np.uint8]:
    """Load an MRI image from disk and convert to RGB uint8.

    Supports common formats (PNG, JPEG, TIFF).  DICOM would require
    pydicom — add that as a future enhancement.
    """
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image at {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def load_mri_from_bytes(data: bytes) -> NDArray[np.uint8]:
    """Decode an in-memory image buffer to an RGB numpy array."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image from bytes")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def preprocess_for_yolo(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Resize to YOLO input dimensions while preserving aspect ratio (letterbox)."""
    h, w = image.shape[:2]
    scale = min(YOLO_INPUT_SIZE[0] / h, YOLO_INPUT_SIZE[1] / w)
    new_h, new_w = int(h * scale), int(w * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    canvas = np.full((*YOLO_INPUT_SIZE, 3), 114, dtype=np.uint8)
    top = (YOLO_INPUT_SIZE[0] - new_h) // 2
    left = (YOLO_INPUT_SIZE[1] - new_w) // 2
    canvas[top : top + new_h, left : left + new_w] = resized
    return canvas


def crop_region(
    image: NDArray[np.uint8],
    bbox: tuple[int, int, int, int],
    padding: int = 10,
) -> NDArray[np.uint8]:
    """Crop a detected region from the image with optional padding.

    Args:
        image: Source RGB image.
        bbox: (x1, y1, x2, y2) bounding box in pixel coordinates.
        padding: Extra pixels around the box.
    """
    h, w = image.shape[:2]
    x1 = max(0, bbox[0] - padding)
    y1 = max(0, bbox[1] - padding)
    x2 = min(w, bbox[2] + padding)
    y2 = min(h, bbox[3] + padding)
    cropped = image[y1:y2, x1:x2]
    return cv2.resize(cropped, CLASSIFIER_INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
