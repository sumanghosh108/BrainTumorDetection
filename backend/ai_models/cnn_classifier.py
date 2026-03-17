"""CNN classifier wrappers — VGG16, VGG19, ResNet101, and a custom lightweight CNN.

Each wrapper loads pretrained ImageNet weights with a replaced final classifier
head fine-tuned on the 4-class brain tumor dataset:
    glioma | meningioma | pituitary | no_tumor
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import torch
import torch.nn as nn
from torchvision import models

from backend.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

NUM_CLASSES = 4
CLASS_NAMES = ["glioma", "meningioma", "no_tumor", "pituitary"]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BaseClassifier(ABC):
    """Common interface for all classification backbones."""

    name: str
    _model: nn.Module | None = None

    @abstractmethod
    def _build_model(self) -> nn.Module:
        """Return a freshly constructed model with the correct head."""

    def load(self, weights_path: str | None = None) -> None:
        model = self._build_model()
        path = weights_path or os.getenv(
            f"{self.name.upper()}_WEIGHTS", f"weights/{self.name}.pt"
        )
        if os.path.isfile(path):
            state = torch.load(path, map_location=DEVICE, weights_only=True)
            model.load_state_dict(state)
            logger.info("classifier_loaded", name=self.name, path=path)
        else:
            logger.warning(
                "classifier_weights_missing",
                name=self.name,
                path=path,
                hint="Model will use random / pretrained-ImageNet weights.",
            )
        model.to(DEVICE).eval()
        self._model = model

    @torch.inference_mode()
    def predict(self, tensor: torch.Tensor) -> tuple[str, float, list[float]]:
        """Run classification on a preprocessed tensor.

        Args:
            tensor: Shape ``(1, 3, 224, 224)`` — already normalised.

        Returns:
            (predicted_class_name, confidence, all_probabilities)
        """
        if self._model is None:
            raise RuntimeError(f"{self.name} model not loaded — call .load() first")

        tensor = tensor.to(DEVICE)
        logits = self._model(tensor)
        probs = torch.softmax(logits, dim=1).squeeze(0)
        conf, idx = probs.max(0)
        return CLASS_NAMES[idx.item()], float(conf.item()), probs.tolist()

    @property
    def model(self) -> nn.Module:
        if self._model is None:
            raise RuntimeError(f"{self.name} not loaded")
        return self._model


# ---------------------------------------------------------------------------
# Concrete classifiers
# ---------------------------------------------------------------------------


class CNNClassifier(BaseClassifier):
    """Lightweight custom CNN for fast inference on CPU."""

    name = "cnn"

    def _build_model(self) -> nn.Module:
        return nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((7, 7)),
            nn.Flatten(),
            nn.Linear(128 * 7 * 7, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, NUM_CLASSES),
        )


class VGG16Classifier(BaseClassifier):
    """VGG-16 with a replaced classifier head."""

    name = "vgg16"

    def _build_model(self) -> nn.Module:
        model = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)
        model.classifier[-1] = nn.Linear(
            model.classifier[-1].in_features, NUM_CLASSES
        )
        return model


class VGG19Classifier(BaseClassifier):
    """VGG-19 with a replaced classifier head."""

    name = "vgg19"

    def _build_model(self) -> nn.Module:
        model = models.vgg19(weights=models.VGG19_Weights.IMAGENET1K_V1)
        model.classifier[-1] = nn.Linear(
            model.classifier[-1].in_features, NUM_CLASSES
        )
        return model


class ResNet101Classifier(BaseClassifier):
    """ResNet-101 with a replaced fully connected layer."""

    name = "resnet101"

    def _build_model(self) -> nn.Module:
        model = models.resnet101(weights=models.ResNet101_Weights.IMAGENET1K_V2)
        model.fc = nn.Linear(model.fc.in_features, NUM_CLASSES)
        return model
