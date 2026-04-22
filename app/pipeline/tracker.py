from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.models import ApprovedTarget, BoundingBox, Detection, TrackingResult

BRIDGE_TRACKING_CONFIDENCE_FLOOR = 0.40


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
