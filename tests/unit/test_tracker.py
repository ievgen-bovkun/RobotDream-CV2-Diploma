from __future__ import annotations

import numpy as np

from app.domain.config import ProcessingConfig
from app.domain.models import BoundingBox, Detection
import app.pipeline.tracker as tracker_module
from app.pipeline.tracker import (
    BaseTracker,
    BRIDGE_TRACKING_CONFIDENCE_FLOOR,
    BridgeTracker,
    OpenCvCsrtTracker,
    build_tracker_for_config,
    is_csrt_available,
)


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


def test_bridge_tracker_marks_track_lost_below_confidence_floor() -> None:
    tracker = BridgeTracker()
    detection = Detection(
        frame_index=100,
        bbox=BoundingBox(x_min=10.0, y_min=20.0, x_max=110.0, y_max=120.0),
        confidence=0.9,
        class_id=0,
        class_name="airplane",
    )
    approved_target = tracker.initialize(target_id="target-1", detection=detection)

    tracking = tracker.track(approved_target=approved_target, frame_index=117)

    assert tracking.bbox is None
    assert tracking.tracking_status == "lost"
    assert tracking.confidence is not None
    assert tracking.confidence < BRIDGE_TRACKING_CONFIDENCE_FLOOR


def test_build_tracker_for_config_returns_bridge_tracker() -> None:
    tracker = build_tracker_for_config(ProcessingConfig(tracker_backend="bridge"))

    assert isinstance(tracker, BridgeTracker)


def test_build_tracker_for_config_returns_csrt_tracker() -> None:
    tracker = build_tracker_for_config(ProcessingConfig(tracker_backend="csrt"))

    if is_csrt_available():
        assert isinstance(tracker, OpenCvCsrtTracker)
    else:
        assert isinstance(tracker, BridgeTracker)


def test_build_tracker_for_config_falls_back_to_bridge_when_csrt_unavailable(monkeypatch) -> None:
    monkeypatch.delattr("app.pipeline.tracker.cv2.TrackerCSRT_create", raising=False)
    legacy = getattr(tracker_module.cv2, "legacy", None)
    if legacy is not None:
        monkeypatch.delattr(legacy, "TrackerCSRT_create", raising=False)

    tracker = build_tracker_for_config(ProcessingConfig(tracker_backend="csrt"))

    assert isinstance(tracker, BridgeTracker)


def test_csrt_tracker_marks_track_lost_when_update_fails() -> None:
    tracker = OpenCvCsrtTracker()
    frame = np.zeros((120, 120, 3), dtype=np.uint8)
    detection = Detection(
        frame_index=10,
        bbox=BoundingBox(x_min=20.0, y_min=20.0, x_max=60.0, y_max=60.0),
        confidence=0.9,
        class_id=0,
        class_name="airplane",
    )
    approved_target = tracker.initialize(target_id="target-1", detection=detection, frame=frame)
    tracker.reset()

    tracking = tracker.track(approved_target=approved_target, frame_index=11, frame=frame)

    assert tracking.bbox is None
    assert tracking.tracking_status == "lost"
    assert tracking.confidence == 0.0
