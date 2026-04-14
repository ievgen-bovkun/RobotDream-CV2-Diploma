from __future__ import annotations

import cv2
import numpy as np

from app.domain.models import Detection
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
        if guidance.estimated_range_m is not None:
            lines.append(
                f"estimated_range_m={guidance.estimated_range_m:.1f} ({guidance.range_estimation_method or 'unknown'})"
            )
        if guidance.target_profile_label is not None:
            lines.append(f"target_profile={guidance.target_profile_label}")

    return lines


def annotate_detection_frame(
    image: np.ndarray,
    detection: Detection | None,
    *,
    header_text: str,
    status_text: str,
    color: tuple[int, int, int],
) -> np.ndarray:
    annotated = image.copy()

    if detection is not None:
        bbox = detection.bbox
        cv2.rectangle(
            annotated,
            (int(bbox.x_min), int(bbox.y_min)),
            (int(bbox.x_max), int(bbox.y_max)),
            color,
            3,
        )
        label = f"{detection.class_name} {detection.confidence:.2f}"
        cv2.putText(
            annotated,
            label,
            (int(bbox.x_min), max(28, int(bbox.y_min) - 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        annotated,
        header_text,
        (24, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        annotated,
        status_text,
        (24, 72),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
        cv2.LINE_AA,
    )
    return annotated
