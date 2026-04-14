from __future__ import annotations

import math

from app.domain.models import (
    BoundingBox,
    CameraOpticsProfile,
    DroneProfile,
    GuidanceCommand,
    GuidanceResult,
    Point,
    TargetProfile,
    VideoMetadata,
)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def calculate_frame_center(metadata: VideoMetadata) -> Point:
    return Point(x=metadata.width / 2.0, y=metadata.height / 2.0)


def calculate_aim_point(
    metadata: VideoMetadata,
    drone_profile: DroneProfile | None = None,
) -> Point:
    frame_center = calculate_frame_center(metadata)
    if drone_profile is None:
        return frame_center
    return Point(
        x=frame_center.x + drone_profile.camera_offset_x_px,
        y=frame_center.y + drone_profile.camera_offset_y_px,
    )


def calculate_target_center(bbox: BoundingBox) -> Point:
    return bbox.center()


def _apply_optics_offset(
    target_center: Point,
    metadata: VideoMetadata,
    camera_profile: CameraOpticsProfile | None = None,
) -> Point:
    if camera_profile is None or camera_profile.lens_model == "rectilinear":
        return target_center

    frame_center = calculate_frame_center(metadata)
    normalized_x = (target_center.x - frame_center.x) / max(metadata.width / 2.0, 1.0)
    normalized_y = (target_center.y - frame_center.y) / max(metadata.height / 2.0, 1.0)
    r2 = normalized_x * normalized_x + normalized_y * normalized_y
    radial = 1.0 + camera_profile.k1 * r2 + camera_profile.k2 * (r2**2) + camera_profile.k3 * (r2**3)

    distorted_x = (
        normalized_x * radial
        + 2.0 * camera_profile.p1 * normalized_x * normalized_y
        + camera_profile.p2 * (r2 + 2.0 * normalized_x * normalized_x)
    )
    distorted_y = (
        normalized_y * radial
        + camera_profile.p1 * (r2 + 2.0 * normalized_y * normalized_y)
        + 2.0 * camera_profile.p2 * normalized_x * normalized_y
    )

    return Point(
        x=frame_center.x + distorted_x * (metadata.width / 2.0),
        y=frame_center.y + distorted_y * (metadata.height / 2.0),
    )


def _estimate_range_from_bbox(
    *,
    bbox: BoundingBox,
    metadata: VideoMetadata,
    target_profile: TargetProfile | None,
    horizontal_fov_deg: float,
    vertical_fov_deg: float,
) -> tuple[float | None, str | None]:
    if target_profile is None:
        return None, None
    if bbox.width <= 1.0 and bbox.height <= 1.0:
        return None, None

    half_width = metadata.width / 2.0
    half_height = metadata.height / 2.0
    if half_width <= 0.0 or half_height <= 0.0:
        return None, None

    focal_x_px = half_width / max(math.tan(math.radians(horizontal_fov_deg / 2.0)), 1e-6)
    focal_y_px = half_height / max(math.tan(math.radians(vertical_fov_deg / 2.0)), 1e-6)

    width_estimate = (
        target_profile.wingspan_m * focal_x_px / bbox.width if bbox.width > 1.0 else None
    )
    height_estimate = (
        target_profile.length_m * focal_y_px / bbox.height if bbox.height > 1.0 else None
    )

    if width_estimate is not None and height_estimate is not None:
        aspect_ratio = bbox.width / max(bbox.height, 1.0)
        if aspect_ratio >= 1.15:
            return width_estimate, "wingspan"
        if aspect_ratio <= 0.85:
            return height_estimate, "length"
        return (width_estimate + height_estimate) / 2.0, "blended"
    if width_estimate is not None:
        return width_estimate, "wingspan"
    if height_estimate is not None:
        return height_estimate, "length"
    return None, None


def _calculate_range_gain(estimated_range_m: float | None) -> float:
    if estimated_range_m is None:
        return 1.0
    reference_range_m = 300.0
    normalized = max(estimated_range_m, 25.0) / reference_range_m
    return _clamp(normalized**0.25, 0.85, 1.2)


def calculate_guidance(
    frame_index: int,
    metadata: VideoMetadata,
    bbox: BoundingBox,
    horizontal_fov_deg: float,
    vertical_fov_deg: float,
    drone_profile: DroneProfile | None = None,
    camera_profile: CameraOpticsProfile | None = None,
    target_profile: TargetProfile | None = None,
) -> GuidanceResult:
    frame_center = calculate_frame_center(metadata)
    aim_point = calculate_aim_point(metadata, drone_profile=drone_profile)
    target_center = _apply_optics_offset(
        calculate_target_center(bbox),
        metadata,
        camera_profile=camera_profile,
    )
    estimated_range_m, range_estimation_method = _estimate_range_from_bbox(
        bbox=bbox,
        metadata=metadata,
        target_profile=target_profile,
        horizontal_fov_deg=horizontal_fov_deg,
        vertical_fov_deg=vertical_fov_deg,
    )

    dx_pixels = target_center.x - aim_point.x
    dy_pixels = target_center.y - aim_point.y

    yaw_offset_deg_approx = (dx_pixels / (metadata.width / 2.0)) * (horizontal_fov_deg / 2.0)
    pitch_offset_deg_approx = -(dy_pixels / (metadata.height / 2.0)) * (vertical_fov_deg / 2.0)

    return GuidanceResult(
        frame_index=frame_index,
        frame_center=frame_center,
        aim_point=aim_point,
        target_center=target_center,
        target_profile_label=target_profile.label if target_profile is not None else None,
        estimated_range_m=estimated_range_m,
        range_estimation_method=range_estimation_method,
        dx_pixels=dx_pixels,
        dy_pixels=dy_pixels,
        yaw_offset_deg_approx=yaw_offset_deg_approx,
        pitch_offset_deg_approx=pitch_offset_deg_approx,
    )


def calculate_guidance_command(
    *,
    guidance: GuidanceResult,
    metadata: VideoMetadata,
    drone_profile: DroneProfile | None = None,
    dead_zone_fraction: float = 0.08,
    auto_engagement: bool = False,
    engagement_distance_threshold_m: float = 2.0,
) -> GuidanceCommand:
    half_width = metadata.width / 2.0
    half_height = metadata.height / 2.0
    dead_zone_x = half_width * dead_zone_fraction
    dead_zone_y = half_height * dead_zone_fraction

    raw_yaw = guidance.dx_pixels / half_width if half_width > 0 else 0.0
    raw_pitch = -guidance.dy_pixels / half_height if half_height > 0 else 0.0

    yaw_command = 0.0 if abs(guidance.dx_pixels) <= dead_zone_x else _clamp(raw_yaw, -1.0, 1.0)
    pitch_command = 0.0 if abs(guidance.dy_pixels) <= dead_zone_y else _clamp(raw_pitch, -1.0, 1.0)
    range_gain = _calculate_range_gain(guidance.estimated_range_m)
    yaw_limit = drone_profile.max_yaw_command_norm if drone_profile is not None else 1.0
    pitch_limit = drone_profile.max_pitch_command_norm if drone_profile is not None else 1.0
    yaw_command = _clamp(yaw_command * range_gain, -yaw_limit, yaw_limit)
    pitch_command = _clamp(pitch_command * range_gain, -pitch_limit, pitch_limit)

    if yaw_command > 0:
        yaw_direction = "right"
    elif yaw_command < 0:
        yaw_direction = "left"
    else:
        yaw_direction = "centered"

    if pitch_command > 0:
        pitch_direction = "up"
    elif pitch_command < 0:
        pitch_direction = "down"
    else:
        pitch_direction = "centered"

    magnitude = _clamp(max(abs(yaw_command), abs(pitch_command)), 0.0, 1.0)
    auto_engagement_triggered = bool(
        auto_engagement
        and guidance.estimated_range_m is not None
        and guidance.estimated_range_m <= engagement_distance_threshold_m
    )

    return GuidanceCommand(
        frame_index=guidance.frame_index,
        yaw_command_norm=yaw_command,
        pitch_command_norm=pitch_command,
        yaw_direction=yaw_direction,
        pitch_direction=pitch_direction,
        magnitude_norm=magnitude,
        is_centered=magnitude == 0.0,
        range_gain=range_gain,
        auto_engagement_triggered=auto_engagement_triggered,
        engagement_distance_threshold_m=engagement_distance_threshold_m,
    )
