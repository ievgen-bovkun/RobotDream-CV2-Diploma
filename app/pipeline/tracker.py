from __future__ import annotations

from app.domain.models import ApprovedTarget, BoundingBox, TrackingResult


class PlaceholderTracker:
    """Simple bridge tracker that keeps the latest detected box between detector refreshes."""

    def track(self, approved_target: ApprovedTarget, frame_index: int) -> TrackingResult:
        frame_delta = max(frame_index - approved_target.approval_frame, 0)
        bbox = approved_target.initial_bbox
        tracked_bbox = BoundingBox(
            x_min=bbox.x_min,
            y_min=bbox.y_min,
            x_max=bbox.x_max,
            y_max=bbox.y_max,
        )
        confidence = max(0.0, approved_target.initial_confidence - frame_delta * 0.03)
        return TrackingResult(
            frame_index=frame_index,
            target_id=approved_target.target_id,
            bbox=tracked_bbox,
            tracking_status="tracking",
            confidence=confidence,
        )
