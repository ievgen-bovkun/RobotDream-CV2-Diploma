from __future__ import annotations

import pytest

from app.domain.models import BoundingBox, CameraOpticsProfile, DroneProfile, VideoMetadata
from app.pipeline.guidance import calculate_aim_point, calculate_frame_center, calculate_guidance


@pytest.fixture
def metadata() -> VideoMetadata:
    return VideoMetadata(width=1280, height=720, fps=30.0, frame_count=180, duration_seconds=6.0)


@pytest.fixture
def right_of_center_bbox() -> BoundingBox:
    return BoundingBox(x_min=760.0, y_min=320.0, x_max=820.0, y_max=380.0)


@pytest.fixture
def offset_multicopter_profile() -> DroneProfile:
    return DroneProfile(
        profile_id="mc_offset",
        label="MC offset",
        drone_type="multicopter",
        camera_offset_x_px=40.0,
        camera_offset_y_px=-20.0,
        control_model="motors",
    )


@pytest.fixture
def wide_angle_camera_profile() -> CameraOpticsProfile:
    return CameraOpticsProfile(
        profile_id="wide",
        label="Wide",
        lens_model="opencv_radial_tangential",
        horizontal_fov_deg=120.0,
        vertical_fov_deg=80.0,
        k1=-0.32,
        k2=0.10,
        p1=0.0,
        p2=0.0,
        k3=-0.02,
    )


def test_calculate_frame_center_x_uses_half_width(metadata: VideoMetadata) -> None:
    center = calculate_frame_center(metadata)
    assert center.x == 640.0


def test_calculate_frame_center_y_uses_half_height(metadata: VideoMetadata) -> None:
    center = calculate_frame_center(metadata)
    assert center.y == 360.0


def test_calculate_aim_point_x_adds_drone_camera_offset(
    metadata: VideoMetadata,
    offset_multicopter_profile: DroneProfile,
) -> None:
    aim_point = calculate_aim_point(metadata, drone_profile=offset_multicopter_profile)

    assert aim_point.x == 680.0


def test_calculate_aim_point_y_adds_drone_camera_offset(
    metadata: VideoMetadata,
    offset_multicopter_profile: DroneProfile,
) -> None:
    aim_point = calculate_aim_point(metadata, drone_profile=offset_multicopter_profile)

    assert aim_point.y == 340.0


def test_calculate_guidance_dx_is_positive_for_target_right_of_center(
    metadata: VideoMetadata,
    right_of_center_bbox: BoundingBox,
) -> None:
    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=right_of_center_bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
    )

    assert result.dx_pixels > 0


def test_calculate_guidance_yaw_is_positive_for_target_right_of_center(
    metadata: VideoMetadata,
    right_of_center_bbox: BoundingBox,
) -> None:
    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=right_of_center_bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
    )

    assert result.yaw_offset_deg_approx > 0


def test_calculate_guidance_uses_offset_aim_point_for_reported_center(
    metadata: VideoMetadata,
    right_of_center_bbox: BoundingBox,
) -> None:
    profile = DroneProfile(
        profile_id="mc_offset_x_only",
        label="MC offset x only",
        drone_type="multicopter",
        camera_offset_x_px=40.0,
        camera_offset_y_px=0.0,
        control_model="motors",
    )
    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=right_of_center_bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
        drone_profile=profile,
    )

    assert result.frame_center.x == 680.0


def test_calculate_guidance_uses_offset_aim_point_for_dx(
    metadata: VideoMetadata,
    right_of_center_bbox: BoundingBox,
) -> None:
    profile = DroneProfile(
        profile_id="mc_offset_x_only",
        label="MC offset x only",
        drone_type="multicopter",
        camera_offset_x_px=40.0,
        camera_offset_y_px=0.0,
        control_model="motors",
    )
    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=right_of_center_bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
        drone_profile=profile,
    )

    assert result.dx_pixels == 110.0


def test_calculate_guidance_keeps_positive_yaw_with_offset_aim_point(
    metadata: VideoMetadata,
    right_of_center_bbox: BoundingBox,
) -> None:
    profile = DroneProfile(
        profile_id="mc_offset_x_only",
        label="MC offset x only",
        drone_type="multicopter",
        camera_offset_x_px=40.0,
        camera_offset_y_px=0.0,
        control_model="motors",
    )
    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=right_of_center_bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
        drone_profile=profile,
    )

    assert result.yaw_offset_deg_approx > 0


def test_calculate_guidance_wide_angle_profile_shifts_edge_target_x_left(
    metadata: VideoMetadata,
    wide_angle_camera_profile: CameraOpticsProfile,
) -> None:
    bbox = BoundingBox(x_min=980.0, y_min=300.0, x_max=1060.0, y_max=380.0)
    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=120.0,
        vertical_fov_deg=80.0,
        camera_profile=wide_angle_camera_profile,
    )

    assert result.target_center.x < 1020.0


def test_calculate_guidance_wide_angle_profile_keeps_positive_dx_for_edge_target(
    metadata: VideoMetadata,
    wide_angle_camera_profile: CameraOpticsProfile,
) -> None:
    bbox = BoundingBox(x_min=980.0, y_min=300.0, x_max=1060.0, y_max=380.0)
    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=120.0,
        vertical_fov_deg=80.0,
        camera_profile=wide_angle_camera_profile,
    )

    assert result.dx_pixels > 0


def test_calculate_guidance_rectilinear_profile_keeps_raw_target_center(
    metadata: VideoMetadata,
) -> None:
    bbox = BoundingBox(x_min=980.0, y_min=300.0, x_max=1060.0, y_max=380.0)
    rectilinear_profile = CameraOpticsProfile(
        profile_id="rect",
        label="Rect",
        lens_model="rectilinear",
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
    )

    result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=bbox,
        horizontal_fov_deg=78.0,
        vertical_fov_deg=49.0,
        camera_profile=rectilinear_profile,
    )

    assert result.target_center.x == 1020.0


def test_calculate_guidance_wide_angle_shifts_edge_target_more_than_near_center_target(
    metadata: VideoMetadata,
    wide_angle_camera_profile: CameraOpticsProfile,
) -> None:
    edge_bbox = BoundingBox(x_min=980.0, y_min=300.0, x_max=1060.0, y_max=380.0)
    near_center_bbox = BoundingBox(x_min=650.0, y_min=320.0, x_max=710.0, y_max=380.0)

    edge_result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=edge_bbox,
        horizontal_fov_deg=120.0,
        vertical_fov_deg=80.0,
        camera_profile=wide_angle_camera_profile,
    )
    center_result = calculate_guidance(
        frame_index=15,
        metadata=metadata,
        bbox=near_center_bbox,
        horizontal_fov_deg=120.0,
        vertical_fov_deg=80.0,
        camera_profile=wide_angle_camera_profile,
    )

    edge_shift = abs(1020.0 - edge_result.target_center.x)
    center_shift = abs(680.0 - center_result.target_center.x)

    assert edge_shift > center_shift
