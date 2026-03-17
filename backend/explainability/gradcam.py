"""Grad-CAM heatmap generation overlaid on original MRI images.

Uses ``pytorch-grad-cam`` to produce visual explanations from the
classification backbone that contributed most to the ensemble decision.
"""

from __future__ import annotations

import io
import uuid
from typing import TYPE_CHECKING

import cv2
import numpy as np
import torch
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

from backend.ai_models.preprocessing import CLASSIFIER_INPUT_SIZE, classifier_transform
from backend.utils.logger import get_logger

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from backend.ai_models.cnn_classifier import BaseClassifier

logger = get_logger(__name__)


def _resolve_target_layer(classifier: BaseClassifier) -> list[torch.nn.Module]:
    """Pick the best convolutional layer for Grad-CAM based on the backbone.

    For VGG variants the last conv block is ``features[-1]``.
    For ResNet variants it's ``layer4[-1]``.
    For the lightweight CNN it's the last Conv2d in the Sequential.
    """
    model = classifier.model
    name = classifier.name

    if "resnet" in name:
        return [model.layer4[-1]]
    if "vgg" in name:
        # Walk backwards to find the last ReLU in the features block
        return [model.features[-1]]
    # Custom CNN — find last Conv2d
    convs = [m for m in model.modules() if isinstance(m, torch.nn.Conv2d)]
    if convs:
        return [convs[-1]]
    raise ValueError(f"Cannot resolve target layer for classifier '{name}'")


def generate_gradcam(
    classifier: BaseClassifier,
    image_rgb: NDArray[np.uint8],
    target_class_idx: int | None = None,
) -> NDArray[np.uint8]:
    """Produce a Grad-CAM heatmap overlay on the original MRI.

    Args:
        classifier: A loaded ``BaseClassifier`` instance.
        image_rgb: The cropped (or full) MRI region as RGB uint8 (any size).
        target_class_idx: Class to explain.  ``None`` means "explain the
            top-predicted class".

    Returns:
        BGR uint8 image (same size as input) with the heatmap overlaid.
    """
    # Prepare input tensor
    resized = cv2.resize(image_rgb, CLASSIFIER_INPUT_SIZE)
    tensor = classifier_transform(resized).unsqueeze(0)

    # Normalised float image for overlay (0-1 range)
    norm_img = resized.astype(np.float32) / 255.0

    target_layers = _resolve_target_layer(classifier)
    targets = [ClassifierOutputTarget(target_class_idx)] if target_class_idx is not None else None

    with GradCAM(model=classifier.model, target_layers=target_layers) as cam:
        grayscale_cam = cam(input_tensor=tensor, targets=targets)
        grayscale_cam = grayscale_cam[0, :]  # first (only) image in batch

    overlay = show_cam_on_image(norm_img, grayscale_cam, use_rgb=True)

    # Scale back to original input size
    oh, ow = image_rgb.shape[:2]
    if (oh, ow) != CLASSIFIER_INPUT_SIZE:
        overlay = cv2.resize(overlay, (ow, oh), interpolation=cv2.INTER_LINEAR)

    logger.info("gradcam_generated", classifier=classifier.name, target_class=target_class_idx)
    return overlay


def gradcam_to_png_bytes(overlay: NDArray[np.uint8]) -> bytes:
    """Encode a Grad-CAM overlay as in-memory PNG bytes for S3 upload."""
    bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
    success, buf = cv2.imencode(".png", bgr)
    if not success:
        raise RuntimeError("Failed to encode Grad-CAM overlay as PNG")
    return buf.tobytes()
