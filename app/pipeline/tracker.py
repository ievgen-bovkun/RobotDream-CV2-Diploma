from __future__ import annotations

from app.domain.models import ApprovedTarget, BoundingBox, TrackingResult


class PlaceholderTracker:
    """Simple tracker that drifts the approved box slightly to exercise downstream contracts."""

    def track(self, approved_target: ApprovedTarget, frame_index: int) -> TrackingResult:
        frame_delta = max(frame_index - approved_target.approval_frame, 0)
        bbox = approved_target.initial_bbox
        tracked_bbox = BoundingBox(
            x_min=bbox.x_min + frame_delta * 2.0,
            y_min=bbox.y_min + frame_delta * 1.0,
            x_max=bbox.x_max + frame_delta * 2.0,
            y_max=bbox.y_max + frame_delta * 1.0,
        )
        confidence = max(0.5, approved_target.initial_confidence - frame_delta * 0.01)
        return TrackingResult(
            frame_index=frame_index,
            target_id=approved_target.target_id,
            bbox=tracked_bbox,
            tracking_status="tracking",
            confidence=confidence,
        )
