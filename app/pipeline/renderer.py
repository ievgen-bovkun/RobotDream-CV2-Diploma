from __future__ import annotations

from app.domain.models import GuidanceResult, TrackingResult


def build_overlay_lines(
    tracking: TrackingResult | None,
    guidance: GuidanceResult | None,
) -> list[str]:
    lines: list[str] = []

    if tracking is not None:
        lines.append(f"tracking_status={tracking.tracking_status}")
        if tracking.confidence is not None:
            lines.append(f"tracking_confidence={tracking.confidence:.2f}")

    if guidance is not None:
        lines.append(
            f"target_offset_pixels=({guidance.dx_pixels:.1f}, {guidance.dy_pixels:.1f})"
        )
        lines.append(
            f"angle_offset_deg=(yaw={guidance.yaw_offset_deg_approx:.2f}, pitch={guidance.pitch_offset_deg_approx:.2f})"
        )

    return lines
