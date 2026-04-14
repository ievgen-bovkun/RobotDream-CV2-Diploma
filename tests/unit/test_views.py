from __future__ import annotations

from app.domain.models import BoundingBox, Detection, GuidanceCommand, GuidanceResult, Point, TrackingResult
from app.pipeline.orchestrator import FramePreview
from app.ui.views import (
    build_custom_video_player_html,
    build_detection_log_entries,
    build_processing_summary_entries,
    build_runtime_overlay_payload,
    select_pipeline_preview_frames,
)


def test_detection_log_entries_show_waiting_state_without_video() -> None:
    entries = build_detection_log_entries(
        uploaded_video_name=None,
        uploaded_video_size=None,
        preview_frames=[],
        auto_replay=False,
    )

    assert ("Runtime Status", "Awaiting uploaded video") in entries
    assert ("Loaded Video", "No video loaded yet") in entries
    assert ("Auto Replay", "Disabled") in entries


def test_detection_log_entries_include_processing_summary() -> None:
    entries = build_detection_log_entries(
        uploaded_video_name="demo.mp4",
        uploaded_video_size=3 * 1024 * 1024,
        preview_frames=[FramePreview(frame_index=15)],
        auto_replay=True,
    )

    assert ("Runtime Status", "Preview processed and ready for review") in entries
    assert ("Auto Replay", "Enabled") in entries
    assert ("Processed Frames", "1") in entries
    assert ("Latest Frame", "15") in entries


def test_detection_log_entries_show_processing_state_while_preview_builds() -> None:
    entries = build_detection_log_entries(
        uploaded_video_name="demo.mp4",
        uploaded_video_size=3 * 1024 * 1024,
        preview_frames=[],
        auto_replay=False,
        is_processing_preview=True,
    )

    assert ("Runtime Status", "Preprocessing uploaded video") in entries
    assert ("Loaded Video", "demo.mp4 (3.00 MB)") in entries


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
        guidance=GuidanceResult(
            frame_index=15,
            frame_center=Point(x=640.0, y=360.0),
            aim_point=Point(x=694.0, y=332.0),
            target_center=Point(x=140.0, y=170.0),
            target_profile_label="Shahed-136",
            estimated_range_m=284.0,
            range_estimation_method="wingspan",
            dx_pixels=-500.0,
            dy_pixels=-190.0,
            yaw_offset_deg_approx=-30.47,
            pitch_offset_deg_approx=12.93,
        ),
        guidance_command=GuidanceCommand(
            frame_index=15,
            yaw_command_norm=-0.78,
            pitch_command_norm=0.53,
            yaw_direction="left",
            pitch_direction="up",
            magnitude_norm=0.78,
            is_centered=False,
            range_gain=1.12,
        ),
    )

    payload = build_runtime_overlay_payload([preview])

    assert payload == [
        {
            "timestamp_seconds": 0.5,
            "frame_index": 15,
            "target_label": "Shahed-136",
            "x_min": 100.0,
            "y_min": 120.0,
            "x_max": 180.0,
            "y_max": 220.0,
            "confidence": 0.77,
            "source": "tracking",
            "tracking_status": "tracking",
            "guidance": {
                "frame_center_x": 640.0,
                "frame_center_y": 360.0,
                "aim_point_x": 694.0,
                "aim_point_y": 332.0,
                "target_center_x": 140.0,
                "target_center_y": 170.0,
                "target_profile_label": "Shahed-136",
                "estimated_range_m": 284.0,
                "range_estimation_method": "wingspan",
                "dx_pixels": -500.0,
                "dy_pixels": -190.0,
                "yaw_offset_deg": -30.47,
                "pitch_offset_deg": 12.93,
            },
            "guidance_command": {
                "yaw_command_norm": -0.78,
                "pitch_command_norm": 0.53,
                "yaw_direction": "left",
                "pitch_direction": "up",
                "magnitude_norm": 0.78,
                "is_centered": False,
                "range_gain": 1.12,
                "auto_engagement_triggered": False,
                "engagement_distance_threshold_m": None,
            },
        }
    ]


def test_select_pipeline_preview_frames_prefers_informative_tail() -> None:
    previews = [
        FramePreview(frame_index=1),
        FramePreview(
            frame_index=2,
            detections=[
                Detection(
                    frame_index=2,
                    bbox=BoundingBox(x_min=1.0, y_min=2.0, x_max=3.0, y_max=4.0),
                    confidence=0.8,
                    class_id=0,
                    class_name="airplane",
                )
            ],
        ),
        FramePreview(frame_index=3),
        FramePreview(
            frame_index=4,
            tracking=TrackingResult(
                frame_index=4,
                target_id="tracked-1",
                bbox=BoundingBox(x_min=10.0, y_min=20.0, x_max=30.0, y_max=40.0),
                tracking_status="tracking",
                confidence=0.7,
            ),
        ),
        FramePreview(frame_index=5),
    ]

    visible_previews, label = select_pipeline_preview_frames(previews)

    assert label == "latest informative frames"
    assert [preview.frame_index for preview in visible_previews] == [4, 2]


def test_build_processing_summary_entries_reports_detection_and_tracking_windows() -> None:
    previews = [
        FramePreview(frame_index=0),
        FramePreview(
            frame_index=3,
            detections=[
                Detection(
                    frame_index=3,
                    bbox=BoundingBox(x_min=1.0, y_min=2.0, x_max=3.0, y_max=4.0),
                    confidence=0.8,
                    class_id=0,
                    class_name="airplane",
                )
            ],
        ),
        FramePreview(
            frame_index=5,
            tracking=TrackingResult(
                frame_index=5,
                target_id="tracked-1",
                bbox=BoundingBox(x_min=10.0, y_min=20.0, x_max=30.0, y_max=40.0),
                tracking_status="tracking",
                confidence=0.7,
            ),
        ),
    ]

    entries = build_processing_summary_entries(previews)

    assert ("Detection Frames", "1") in entries
    assert ("Tracking Frames", "1") in entries
    assert ("First Detection", "3") in entries
    assert ("Last Tracking", "5") in entries


def test_custom_video_player_html_uses_aim_point_fields_for_guidance_line() -> None:
    preview = FramePreview(
        frame_index=7,
        timestamp_seconds=0.25,
        tracking=TrackingResult(
            frame_index=7,
            target_id="tracked-1",
            bbox=BoundingBox(x_min=100.0, y_min=120.0, x_max=180.0, y_max=220.0),
            tracking_status="tracking",
            confidence=0.77,
        ),
        guidance=GuidanceResult(
            frame_index=7,
            frame_center=Point(x=640.0, y=360.0),
            aim_point=Point(x=694.0, y=332.0),
            target_center=Point(x=140.0, y=170.0),
            target_profile_label="Shahed-136",
            estimated_range_m=284.0,
            range_estimation_method="wingspan",
            dx_pixels=-554.0,
            dy_pixels=-162.0,
            yaw_offset_deg_approx=-33.74,
            pitch_offset_deg_approx=11.03,
        ),
        guidance_command=GuidanceCommand(
            frame_index=7,
            yaw_command_norm=-0.86,
            pitch_command_norm=0.45,
            yaw_direction="left",
            pitch_direction="up",
            magnitude_norm=0.86,
            is_centered=False,
            range_gain=1.12,
            auto_engagement_triggered=False,
            engagement_distance_threshold_m=None,
        ),
    )

    html = build_custom_video_player_html(
        video_bytes=b"demo-video",
        mime_type="video/mp4",
        auto_replay=False,
        play_request_nonce=1,
        pause_request_nonce=0,
        guidance_armed=True,
        guidance_arm_nonce=1,
        player_storage_key="player-1",
        preview_frames=[preview],
    )

    assert "aim_point_x" in html
    assert "aim_point_y" in html
    assert "activeOverlay.guidance.aim_point_x" in html


def test_custom_video_player_html_contains_neutralized_overlay_markup() -> None:
    preview = FramePreview(
        frame_index=12,
        timestamp_seconds=0.4,
        tracking=TrackingResult(
            frame_index=12,
            target_id="tracked-1",
            bbox=BoundingBox(x_min=220.0, y_min=180.0, x_max=980.0, y_max=640.0),
            tracking_status="tracking",
            confidence=0.92,
        ),
        guidance=GuidanceResult(
            frame_index=12,
            frame_center=Point(x=640.0, y=360.0),
            aim_point=Point(x=640.0, y=360.0),
            target_center=Point(x=600.0, y=350.0),
            target_profile_label="Shahed-136",
            estimated_range_m=1.7,
            range_estimation_method="blended",
            dx_pixels=-40.0,
            dy_pixels=-10.0,
            yaw_offset_deg_approx=-2.4,
            pitch_offset_deg_approx=0.7,
        ),
        guidance_command=GuidanceCommand(
            frame_index=12,
            yaw_command_norm=-0.1,
            pitch_command_norm=0.05,
            yaw_direction="left",
            pitch_direction="up",
            magnitude_norm=0.1,
            is_centered=False,
            range_gain=1.25,
            auto_engagement_triggered=True,
            engagement_distance_threshold_m=2.0,
        ),
    )

    html = build_custom_video_player_html(
        video_bytes=b"demo-video",
        mime_type="video/mp4",
        auto_replay=False,
        play_request_nonce=1,
        pause_request_nonce=0,
        guidance_armed=True,
        guidance_arm_nonce=1,
        player_storage_key="player-2",
        preview_frames=[preview],
    )

    assert "Neutralized" in html
    assert "auto_engagement_triggered" in html
