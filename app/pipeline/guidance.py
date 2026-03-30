from __future__ import annotations

from app.domain.models import BoundingBox, GuidanceResult, Point, VideoMetadata


def calculate_frame_center(metadata: VideoMetadata) -> Point:
    return Point(x=metadata.width / 2.0, y=metadata.height / 2.0)


def calculate_target_center(bbox: BoundingBox) -> Point:
    return bbox.center()


def calculate_guidance(
    frame_index: int,
    metadata: VideoMetadata,
    bbox: BoundingBox,
    horizontal_fov_deg: float,
    vertical_fov_deg: float,
) -> GuidanceResult:
    frame_center = calculate_frame_center(metadata)
    target_center = calculate_target_center(bbox)

    dx_pixels = target_center.x - frame_center.x
    dy_pixels = target_center.y - frame_center.y

    yaw_offset_deg_approx = (dx_pixels / (metadata.width / 2.0)) * (horizontal_fov_deg / 2.0)
    pitch_offset_deg_approx = -(dy_pixels / (metadata.height / 2.0)) * (vertical_fov_deg / 2.0)

    return GuidanceResult(
        frame_index=frame_index,
        frame_center=frame_center,
        target_center=target_center,
        dx_pixels=dx_pixels,
        dy_pixels=dy_pixels,
        yaw_offset_deg_approx=yaw_offset_deg_approx,
        pitch_offset_deg_approx=pitch_offset_deg_approx,
    )
