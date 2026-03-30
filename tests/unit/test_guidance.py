from __future__ import annotations

from app.domain.models import BoundingBox, VideoMetadata
from app.pipeline.guidance import calculate_frame_center, calculate_guidance


def test_calculate_frame_center_uses_half_dimensions() -> None:
    metadata = VideoMetadata(width=1280, height=720, fps=30.0, frame_count=180, duration_seconds=6.0)

    center = calculate_frame_center(metadata)

    assert center.x == 640.0
    assert center.y == 360.0


def test_calculate_guidance_reports_positive_yaw_for_target_right_of_center() -> None:
    metadata = VideoMetadata(width=1280, height=720, fps=30.0, frame_count=180, duration_seconds=6.0)
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
