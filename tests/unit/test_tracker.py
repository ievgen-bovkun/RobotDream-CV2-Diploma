from __future__ import annotations

from app.domain.models import BoundingBox, Detection
from app.pipeline.tracker import BaseTracker, BridgeTracker


def test_bridge_tracker_implements_base_tracker_contract() -> None:
    tracker = BridgeTracker()

    assert isinstance(tracker, BaseTracker)


def test_bridge_tracker_initializes_approved_target_from_detection() -> None:
    tracker = BridgeTracker()
    detection = Detection(
        frame_index=100,
        bbox=BoundingBox(x_min=10.0, y_min=20.0, x_max=110.0, y_max=120.0),
        confidence=0.9,
        class_id=0,
        class_name="airplane",
    )

    approved_target = tracker.initialize(target_id="target-1", detection=detection)

    assert approved_target.target_id == "target-1"
    assert approved_target.approval_frame == 100
    assert approved_target.initial_bbox == detection.bbox
    assert approved_target.initial_confidence == 0.9


def test_bridge_tracker_holds_latest_bbox_between_detection_refreshes() -> None:
    tracker = BridgeTracker()
    detection = Detection(
        frame_index=100,
        bbox=BoundingBox(x_min=10.0, y_min=20.0, x_max=110.0, y_max=120.0),
        confidence=0.9,
        class_id=0,
        class_name="airplane",
    )
    approved_target = tracker.initialize(target_id="target-1", detection=detection)

    tracking = tracker.track(approved_target=approved_target, frame_index=107)

    assert tracking.bbox == approved_target.initial_bbox
    assert tracking.tracking_status == "tracking"
    assert tracking.confidence is not None
    assert 0.0 <= tracking.confidence < approved_target.initial_confidence
