from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from typing import Any

import cv2

if TYPE_CHECKING:
    from app.domain.config import ProcessingConfig

from app.domain.models import ApprovedTarget, BoundingBox, Detection, TrackingResult

BRIDGE_TRACKING_CONFIDENCE_FLOOR = 0.55


class BaseTracker(ABC):
    """Tracking contract kept intentionally small so implementations stay swappable."""

    backend_name: str = "base"

    def initialize(
        self,
        *,
        target_id: str,
        detection: Detection,
        frame: Any | None = None,
    ) -> ApprovedTarget:
        return ApprovedTarget(
            target_id=target_id,
            approval_frame=detection.frame_index,
            initial_bbox=detection.bbox,
            initial_confidence=detection.confidence,
        )

    def refresh(
        self,
        *,
        approved_target: ApprovedTarget,
        detection: Detection,
        frame: Any | None = None,
    ) -> ApprovedTarget:
        return ApprovedTarget(
            target_id=approved_target.target_id,
            approval_frame=detection.frame_index,
            initial_bbox=detection.bbox,
            initial_confidence=detection.confidence,
        )

    @abstractmethod
    def track(
        self,
        *,
        approved_target: ApprovedTarget,
        frame_index: int,
        frame: Any | None = None,
    ) -> TrackingResult:
        raise NotImplementedError

    def reset(self) -> None:
        """Hook for stateful trackers like CSRT/KCF."""


class TrackerUnavailableError(RuntimeError):
    """Raised when a requested tracker backend is unavailable in the environment."""


def is_csrt_available() -> bool:
    if hasattr(cv2, "TrackerCSRT_create"):
        return True
    legacy = getattr(cv2, "legacy", None)
    return legacy is not None and hasattr(legacy, "TrackerCSRT_create")


def _create_csrt_tracker() -> Any:
    if hasattr(cv2, "TrackerCSRT_create"):
        return cv2.TrackerCSRT_create()
    legacy = getattr(cv2, "legacy", None)
    if legacy is not None and hasattr(legacy, "TrackerCSRT_create"):
        return legacy.TrackerCSRT_create()
    raise TrackerUnavailableError(
        "CSRT tracker is unavailable in the current OpenCV build. Install an OpenCV contrib build with CSRT support."
    )


def _bbox_to_cv_rect(bbox: BoundingBox) -> tuple[float, float, float, float]:
    return (
        int(round(bbox.x_min)),
        int(round(bbox.y_min)),
        int(round(bbox.width)),
        int(round(bbox.height)),
    )


def _cv_rect_to_bbox(rect: tuple[float, float, float, float]) -> BoundingBox:
    x, y, width, height = rect
    return BoundingBox(
        x_min=float(x),
        y_min=float(y),
        x_max=float(x + width),
        y_max=float(y + height),
    )


class BridgeTracker(BaseTracker):
    """Simple bridge tracker that keeps the latest detected box between detector refreshes."""

    backend_name = "bridge"

    def track(
        self,
        *,
        approved_target: ApprovedTarget,
        frame_index: int,
        frame: Any | None = None,
    ) -> TrackingResult:
        frame_delta = max(frame_index - approved_target.approval_frame, 0)
        bbox = approved_target.initial_bbox
        tracked_bbox = BoundingBox(
            x_min=bbox.x_min,
            y_min=bbox.y_min,
            x_max=bbox.x_max,
            y_max=bbox.y_max,
        )
        confidence = max(0.0, approved_target.initial_confidence - frame_delta * 0.03)
        if confidence < BRIDGE_TRACKING_CONFIDENCE_FLOOR:
            return TrackingResult(
                frame_index=frame_index,
                target_id=approved_target.target_id,
                bbox=None,
                tracking_status="lost",
                confidence=confidence,
            )
        return TrackingResult(
            frame_index=frame_index,
            target_id=approved_target.target_id,
            bbox=tracked_bbox,
            tracking_status="tracking",
            confidence=confidence,
        )


# Backward-compatible alias while the rest of the codebase migrates terminology.
PlaceholderTracker = BridgeTracker


class OpenCvCsrtTracker(BaseTracker):
    backend_name = "csrt"

    def __init__(self) -> None:
        self._tracker: Any | None = None

    def initialize(
        self,
        *,
        target_id: str,
        detection: Detection,
        frame: Any | None = None,
    ) -> ApprovedTarget:
        if frame is None:
            raise ValueError("CSRT tracker requires a frame during initialization")
        approved_target = super().initialize(
            target_id=target_id,
            detection=detection,
            frame=frame,
        )
        self._tracker = _create_csrt_tracker()
        self._tracker.init(frame, _bbox_to_cv_rect(detection.bbox))
        return approved_target

    def refresh(
        self,
        *,
        approved_target: ApprovedTarget,
        detection: Detection,
        frame: Any | None = None,
    ) -> ApprovedTarget:
        if frame is None:
            raise ValueError("CSRT tracker requires a frame during refresh")
        refreshed_target = super().refresh(
            approved_target=approved_target,
            detection=detection,
            frame=frame,
        )
        self._tracker = _create_csrt_tracker()
        self._tracker.init(frame, _bbox_to_cv_rect(detection.bbox))
        return refreshed_target

    def track(
        self,
        *,
        approved_target: ApprovedTarget,
        frame_index: int,
        frame: Any | None = None,
    ) -> TrackingResult:
        if frame is None:
            raise ValueError("CSRT tracker requires a frame during track()")
        if self._tracker is None:
            return TrackingResult(
                frame_index=frame_index,
                target_id=approved_target.target_id,
                bbox=None,
                tracking_status="lost",
                confidence=0.0,
            )
        ok, rect = self._tracker.update(frame)
        if not ok:
            return TrackingResult(
                frame_index=frame_index,
                target_id=approved_target.target_id,
                bbox=None,
                tracking_status="lost",
                confidence=0.0,
            )
        return TrackingResult(
            frame_index=frame_index,
            target_id=approved_target.target_id,
            bbox=_cv_rect_to_bbox(rect),
            tracking_status="tracking",
            confidence=approved_target.initial_confidence,
        )

    def reset(self) -> None:
        self._tracker = None


def build_tracker_for_config(config: "ProcessingConfig") -> BaseTracker:
    if config.tracker_backend == "bridge":
        return BridgeTracker()
    if config.tracker_backend == "csrt":
        if not is_csrt_available():
            return BridgeTracker()
        return OpenCvCsrtTracker()
    raise ValueError(f"Unsupported tracker backend: {config.tracker_backend}")
