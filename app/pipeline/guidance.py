from __future__ import annotations

from app.domain.models import (
    BoundingBox,
    CameraOpticsProfile,
    DroneProfile,
    GuidanceResult,
    Point,
    VideoMetadata,
)


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

    distorted_x = normalized_x * radial + 2.0 * camera_profile.p1 * normalized_x * normalized_y + camera_profile.p2 * (r2 + 2.0 * normalized_x * normalized_x)
    distorted_y = normalized_y * radial + camera_profile.p1 * (r2 + 2.0 * normalized_y * normalized_y) + 2.0 * camera_profile.p2 * normalized_x * normalized_y

    return Point(
        x=frame_center.x + distorted_x * (metadata.width / 2.0),
        y=frame_center.y + distorted_y * (metadata.height / 2.0),
    )


def calculate_guidance(
    frame_index: int,
    metadata: VideoMetadata,
    bbox: BoundingBox,
    horizontal_fov_deg: float,
    vertical_fov_deg: float,
    drone_profile: DroneProfile | None = None,
    camera_profile: CameraOpticsProfile | None = None,
) -> GuidanceResult:
    aim_point = calculate_aim_point(metadata, drone_profile=drone_profile)
    target_center = _apply_optics_offset(
        calculate_target_center(bbox),
        metadata,
        camera_profile=camera_profile,
    )

    dx_pixels = target_center.x - aim_point.x
    dy_pixels = target_center.y - aim_point.y

    yaw_offset_deg_approx = (dx_pixels / (metadata.width / 2.0)) * (horizontal_fov_deg / 2.0)
    pitch_offset_deg_approx = -(dy_pixels / (metadata.height / 2.0)) * (vertical_fov_deg / 2.0)

    return GuidanceResult(
        frame_index=frame_index,
        frame_center=aim_point,
        target_center=target_center,
        dx_pixels=dx_pixels,
        dy_pixels=dy_pixels,
        yaw_offset_deg_approx=yaw_offset_deg_approx,
        pitch_offset_deg_approx=pitch_offset_deg_approx,
    )
