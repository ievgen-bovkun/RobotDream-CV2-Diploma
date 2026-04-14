from __future__ import annotations

import pytest

from app.domain.models import BoundingBox, CameraOpticsProfile, DroneProfile, TargetProfile, VideoMetadata
from app.pipeline.guidance import (
    calculate_aim_point,
    calculate_frame_center,
    calculate_guidance,
    calculate_guidance_command,
)


@pytest.fixture
def metadata() -> VideoMetadata:
    return VideoMetadata(width=1280, height=720, fps=30.0, frame_count=180, duration_seconds=6.0)


@pytest.fixture
def offset_multicopter_profile() -> DroneProfile:
    return DroneProfile(
        profile_id="multicopter_offset_camera",
        label="Multicopter / Offset Camera",
        drone_type="multicopter",
        camera_offset_x_px=48.0,
        camera_offset_y_px=-24.0,
        control_model="motors",
        max_yaw_command_norm=0.95,
        max_pitch_command_norm=0.90,
    )


@pytest.fixture
def wide_angle_camera_profile() -> CameraOpticsProfile:
    return CameraOpticsProfile(
        profile_id="wide_angle_drone",
        label="Wide Angle Drone Camera",
        lens_model="opencv_radial_tangential",
        horizontal_fov_deg=120.0,
        vertical_fov_deg=80.0,
        k1=-0.32,
        k2=0.10,
        p1=0.0,
        p2=0.0,
        k3=-0.02,
    )


@pytest.fixture
def shahed_target_profile() -> TargetProfile:
    return TargetProfile(
        profile_id="shahed_136",
        label="Shahed-136",
        wingspan_m=2.5,
        length_m=3.5,
        cruise_speed_kmh=185.0,
        average_speed_kmh=170.0,
    )


def test_calculate_frame_center_uses_half_dimensions(metadata: VideoMetadata) -> None:
    center = calculate_frame_center(metadata)

    assert center.x == 640.0
    assert center.y == 360.0


def test_calculate_aim_point_uses_drone_camera_offset(
    metadata: VideoMetadata,
    offset_multicopter_profile: DroneProfile,
) -> None:
    aim_point = calculate_aim_point(metadata, drone_profile=offset_multicopter_profile)

    assert aim_point.x == 688.0
    assert aim_point.y == 336.0


def test_calculate_guidance_reports_positive_yaw_for_target_right_of_center(
    metadata: VideoMetadata,
) -> None:
    bbox = BoundingBox(x_min=760.0, y_min=320.0, x_max=820.0, y_max=380.0)

    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
    )

    assert result.dx_pixels > 0
    assert result.yaw_offset_deg_approx > 0
    assert result.aim_point.x == 640.0
    assert result.aim_point.y == 360.0


def test_calculate_guidance_uses_offset_aim_point(
    metadata: VideoMetadata,
    offset_multicopter_profile: DroneProfile,
) -> None:
    bbox = BoundingBox(x_min=660.0, y_min=330.0, x_max=700.0, y_max=370.0)

    centered = calculate_guidance(
        frame_index=11,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
    )
    offset = calculate_guidance(
        frame_index=11,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
        drone_profile=offset_multicopter_profile,
    )

    assert centered.dx_pixels > 0
    assert offset.dx_pixels < centered.dx_pixels
    assert offset.aim_point.x == 688.0
    assert offset.aim_point.y == 336.0


def test_calculate_guidance_wide_angle_profile_shifts_edge_target_x_left(
    metadata: VideoMetadata,
    wide_angle_camera_profile: CameraOpticsProfile,
) -> None:
    bbox = BoundingBox(x_min=1120.0, y_min=320.0, x_max=1180.0, y_max=380.0)

    rectilinear = calculate_guidance(
        frame_index=18,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=120.0,
        vertical_fov_deg=80.0,
    )
    wide_angle = calculate_guidance(
        frame_index=18,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=120.0,
        vertical_fov_deg=80.0,
        camera_profile=wide_angle_camera_profile,
    )

    assert wide_angle.target_center.x < rectilinear.target_center.x


def test_calculate_guidance_estimates_range_from_bbox_width(
    metadata: VideoMetadata,
    shahed_target_profile: TargetProfile,
) -> None:
    bbox = BoundingBox(x_min=500.0, y_min=250.0, x_max=700.0, y_max=350.0)

    guidance = calculate_guidance(
        frame_index=20,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
        target_profile=shahed_target_profile,
    )

    assert guidance.estimated_range_m is not None
    assert guidance.estimated_range_m > 0.0
    assert guidance.range_estimation_method in {"wingspan", "blended", "length"}
    assert guidance.target_profile_label == "Shahed-136"


def test_calculate_guidance_command_returns_centered_in_dead_zone(
    metadata: VideoMetadata,
) -> None:
    bbox = BoundingBox(x_min=620.0, y_min=340.0, x_max=660.0, y_max=380.0)
    guidance = calculate_guidance(
        frame_index=8,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
    )

    command = calculate_guidance_command(guidance=guidance, metadata=metadata)

    assert command.is_centered is True
    assert command.yaw_command_norm == 0.0
    assert command.pitch_command_norm == 0.0
    assert command.yaw_direction == "centered"
    assert command.pitch_direction == "centered"
    assert command.range_gain == 1.0


def test_calculate_guidance_command_points_right_and_up_for_top_right_target(
    metadata: VideoMetadata,
) -> None:
    bbox = BoundingBox(x_min=920.0, y_min=120.0, x_max=980.0, y_max=180.0)
    guidance = calculate_guidance(
        frame_index=12,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
    )

    command = calculate_guidance_command(guidance=guidance, metadata=metadata)

    assert command.is_centered is False
    assert command.yaw_command_norm > 0.0
    assert command.pitch_command_norm > 0.0
    assert command.yaw_direction == "right"
    assert command.pitch_direction == "up"


def test_calculate_guidance_command_respects_drone_profile_limits_and_range_gain(
    metadata: VideoMetadata,
    offset_multicopter_profile: DroneProfile,
    shahed_target_profile: TargetProfile,
) -> None:
    bbox = BoundingBox(x_min=1120.0, y_min=90.0, x_max=1240.0, y_max=180.0)
    guidance = calculate_guidance(
        frame_index=24,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
        target_profile=shahed_target_profile,
    )

    command = calculate_guidance_command(
        guidance=guidance,
        metadata=metadata,
        drone_profile=offset_multicopter_profile,
    )

    assert command.range_gain >= 0.85
    assert abs(command.yaw_command_norm) <= offset_multicopter_profile.max_yaw_command_norm
    assert abs(command.pitch_command_norm) <= offset_multicopter_profile.max_pitch_command_norm


def test_calculate_guidance_command_triggers_auto_engagement_inside_distance_threshold(
    metadata: VideoMetadata,
    shahed_target_profile: TargetProfile,
) -> None:
    bbox = BoundingBox(x_min=110.0, y_min=110.0, x_max=1170.0, y_max=670.0)
    guidance = calculate_guidance(
        frame_index=42,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
        target_profile=shahed_target_profile,
    )

    command = calculate_guidance_command(
        guidance=guidance,
        metadata=metadata,
        auto_engagement=True,
        engagement_distance_threshold_m=2.0,
    )

    assert guidance.estimated_range_m is not None
    assert guidance.estimated_range_m <= 2.0
    assert command.auto_engagement_triggered is True
    assert command.engagement_distance_threshold_m == 2.0
