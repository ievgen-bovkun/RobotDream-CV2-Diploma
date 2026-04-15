from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any

import torch
from ultralytics import YOLO, YOLOWorld

from app.domain.config import ProcessingConfig
from app.domain.models import BoundingBox, Detection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YOLO_MODEL_PATH = PROJECT_ROOT / "models" / "weights" / "yolo11n.pt"
DEFAULT_OPEN_VOCAB_MODEL_PATH = PROJECT_ROOT / "models" / "weights" / "yolov8s-world.pt"
TARGET_LABELS = frozenset({"airplane"})


@lru_cache(maxsize=4)
def _load_cached_yolo_model(model_path: str) -> Any:
    return YOLO(model_path)


@lru_cache(maxsize=8)
def _load_cached_open_vocab_model(model_path: str, prompt_terms: tuple[str, ...]) -> Any:
    model = YOLOWorld(model_path)
    model.set_classes(list(prompt_terms))
    return model


class DetectorUnavailableError(RuntimeError):
    """Raised when a detector backend cannot be loaded locally."""


def resolve_detector_device(requested_device: str) -> str:
    normalized_device = requested_device.strip().lower()
    if normalized_device == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    if normalized_device == "mps":
        if not torch.backends.mps.is_built():
            raise DetectorUnavailableError(
                "This PyTorch build does not include MPS support. Reinstall an Apple Silicon PyTorch build."
            )
        if not torch.backends.mps.is_available():
            raise DetectorUnavailableError(
                "MPS was requested, but torch.backends.mps.is_available() is false in the current environment."
            )
        return "mps"
    if normalized_device == "cpu":
        return "cpu"
    raise ValueError(f"Unsupported detector device: {requested_device}")


class BaseDetector(ABC):
    backend_name: str = "base"

    def detect(self, frame_index: int, frame: Any | None = None) -> list[Detection]:
        return self.filter_target_detections(self.predict(frame_index=frame_index, frame=frame))

    @abstractmethod
    def predict(self, frame_index: int, frame: Any | None = None) -> list[Detection]:
        raise NotImplementedError

    def filter_target_detections(self, detections: list[Detection]) -> list[Detection]:
        return detections


class PlaceholderDetector(BaseDetector):
    """Deterministic stand-in kept for the no-video preview path."""

    backend_name = "placeholder"

    def predict(self, frame_index: int, frame: Any | None = None) -> list[Detection]:
        if frame_index > 0 and frame_index % 15 == 0:
            return [
                Detection(
                    frame_index=frame_index,
                    bbox=BoundingBox(
                        x_min=640.0,
                        y_min=300.0,
                        x_max=740.0,
                        y_max=360.0,
                    ),
                    confidence=0.82,
                    class_id=0,
                    class_name="drone-placeholder",
                )
            ]
        return []


class UltralyticsDetector(BaseDetector, ABC):
    def __init__(
        self,
        *,
        model_path: Path,
        config: ProcessingConfig,
    ) -> None:
        self.model_path = model_path
        self.config = config
        self._model: Any | None = None
        self._resolved_device: str | None = None

    @property
    def model(self) -> Any:
        if self._model is None:
            if not self.model_path.exists():
                raise DetectorUnavailableError(
                    f"Detector weights not found at {self.model_path}. "
                    "Download the required model weights before running real inference."
                )
            self._model = self._load_model()
        return self._model

    @property
    def resolved_device(self) -> str:
        if self._resolved_device is None:
            self._resolved_device = resolve_detector_device(self.config.detector_device)
        return self._resolved_device

    @abstractmethod
    def _load_model(self) -> Any:
        raise NotImplementedError

    def _normalize_frame(self, frame: Any | None) -> Any:
        if frame is None:
            raise ValueError("A real detector requires an image frame")
        return frame

    def predict(self, frame_index: int, frame: Any | None = None) -> list[Detection]:
        normalized_frame = self._normalize_frame(frame)
        result = self.model.predict(
            source=normalized_frame,
            conf=self.config.detection_threshold,
            iou=self.config.nms_iou_threshold,
            imgsz=self.config.input_size,
            max_det=self.config.max_detections,
            device=self.resolved_device,
            verbose=False,
        )[0]

        detections: list[Detection] = []
        names = result.names
        boxes = result.boxes
        if boxes is None:
            return detections

        for box in boxes:
            cls_id = int(box.cls.item())
            confidence = float(box.conf.item())
            x_min, y_min, x_max, y_max = [float(value) for value in box.xyxy[0].tolist()]
            detections.append(
                Detection(
                    frame_index=frame_index,
                    bbox=BoundingBox(
                        x_min=x_min,
                        y_min=y_min,
                        x_max=x_max,
                        y_max=y_max,
                    ),
                    confidence=confidence,
                    class_id=cls_id,
                    class_name=str(names[cls_id]),
                )
            )

        detections.sort(key=lambda detection: detection.confidence, reverse=True)
        return detections


class UltralyticsYoloDetector(UltralyticsDetector):
    backend_name = "yolo"

    def _load_model(self) -> Any:
        return _load_cached_yolo_model(str(self.model_path))

    def filter_target_detections(self, detections: list[Detection]) -> list[Detection]:
        return [
            detection
            for detection in detections
            if detection.class_name.lower() in TARGET_LABELS
        ]


class UltralyticsOpenVocabDetector(UltralyticsDetector):
    backend_name = "open_vocab"

    def _load_model(self) -> Any:
        return _load_cached_open_vocab_model(
            str(self.model_path),
            tuple(self.config.prompt_terms),
        )


def build_detector_for_config(config: ProcessingConfig) -> BaseDetector:
    if config.detector_backend == "yolo":
        return UltralyticsYoloDetector(
            model_path=DEFAULT_YOLO_MODEL_PATH,
            config=config,
        )
    if config.detector_backend == "open_vocab":
        return UltralyticsOpenVocabDetector(
            model_path=DEFAULT_OPEN_VOCAB_MODEL_PATH,
            config=config,
        )
    raise ValueError(f"Unsupported detector backend: {config.detector_backend}")
