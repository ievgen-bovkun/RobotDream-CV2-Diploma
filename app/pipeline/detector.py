from __future__ import annotations

from app.domain.models import BoundingBox, Detection


class PlaceholderDetector:
    """Deterministic stand-in for later YOLO integration."""

    def detect(self, frame_index: int) -> list[Detection]:
        if frame_index > 0 and frame_index % 15 == 0:
            return [
                Detection(
                    frame_index=frame_index,
                    bbox=BoundingBox(
                        x_min=640.0,
                        y_min=300.0,
                        x_max=740.0,
                        y_max=360.0,
                    ),
                    confidence=0.82,
                    class_id=0,
                    class_name="drone-placeholder",
                )
            ]
        return []
