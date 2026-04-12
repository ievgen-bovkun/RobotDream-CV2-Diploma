from __future__ import annotations

from app.domain.models import ApprovedTarget, BoundingBox
from app.pipeline.tracker import PlaceholderTracker


def test_tracker_holds_latest_bbox_between_detection_refreshes() -> None:
    tracker = PlaceholderTracker()
    approved_target = ApprovedTarget(
        target_id="target-1",
        approval_frame=100,
        initial_bbox=BoundingBox(x_min=10.0, y_min=20.0, x_max=110.0, y_max=120.0),
        initial_confidence=0.9,
    )

    tracking = tracker.track(approved_target, frame_index=107)

    assert tracking.bbox == approved_target.initial_bbox
    assert tracking.tracking_status == "tracking"
    assert tracking.confidence is not None
    assert 0.0 <= tracking.confidence < approved_target.initial_confidence
