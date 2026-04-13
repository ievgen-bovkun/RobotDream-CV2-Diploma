from __future__ import annotations

from app.domain.models import BoundingBox, Detection, TrackingResult
from app.pipeline.orchestrator import FramePreview
from app.ui.views import build_detection_log_entries, build_runtime_overlay_payload


def test_detection_log_entries_show_waiting_state_without_video() -> None:
    entries = build_detection_log_entries(
        uploaded_video_name=None,
        uploaded_video_size=None,
        preview_frames=[],
        auto_replay=False,
    )

    assert ("Status", "Awaiting uploaded video") in entries
    assert ("Video", "No video loaded yet") in entries
    assert ("Replay", "Off") in entries


def test_detection_log_entries_include_processing_summary() -> None:
    entries = build_detection_log_entries(
        uploaded_video_name="demo.mp4",
        uploaded_video_size=3 * 1024 * 1024,
        preview_frames=[FramePreview(frame_index=15)],
        auto_replay=True,
    )

    assert ("Status", "Preview processed and ready for review") in entries
    assert ("Replay", "On") in entries
    assert ("Processed Frames", "1") in entries
    assert ("Frame", "15") in entries


def test_detection_log_entries_show_processing_state_while_preview_builds() -> None:
    entries = build_detection_log_entries(
        uploaded_video_name="demo.mp4",
        uploaded_video_size=3 * 1024 * 1024,
        preview_frames=[],
        auto_replay=False,
        is_processing_preview=True,
    )

    assert ("Status", "Processing uploaded video preview") in entries
    assert ("Video", "demo.mp4 (3.00 MB)") in entries


def test_runtime_overlay_payload_prefers_tracking_bbox_when_available() -> None:
    preview = FramePreview(
        frame_index=15,
        timestamp_seconds=0.5,
        detections=[
            Detection(
                frame_index=15,
                bbox=BoundingBox(x_min=10.0, y_min=20.0, x_max=30.0, y_max=40.0),
                confidence=0.81,
                class_id=0,
                class_name="drone",
            )
        ],
        tracking=TrackingResult(
            frame_index=15,
            target_id="tracked-1",
            bbox=BoundingBox(x_min=100.0, y_min=120.0, x_max=180.0, y_max=220.0),
            tracking_status="tracking",
            confidence=0.77,
        ),
    )

    payload = build_runtime_overlay_payload([preview])

    assert payload == [
        {
            "timestamp_seconds": 0.5,
            "frame_index": 15,
            "x_min": 100.0,
            "y_min": 120.0,
            "x_max": 180.0,
            "y_max": 220.0,
            "confidence": 0.77,
            "source": "tracking",
        }
    ]
