from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Point:
    x: float
    y: float


@dataclass(slots=True, frozen=True)
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    def center(self) -> Point:
        return Point(
            x=self.x_min + self.width / 2.0,
            y=self.y_min + self.height / 2.0,
        )


@dataclass(slots=True, frozen=True)
class VideoMetadata:
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float


@dataclass(slots=True, frozen=True)
class Detection:
    frame_index: int
    bbox: BoundingBox
    confidence: float
    class_id: int
    class_name: str


@dataclass(slots=True, frozen=True)
class ApprovedTarget:
    target_id: str
    approval_frame: int
    initial_bbox: BoundingBox
    initial_confidence: float


@dataclass(slots=True, frozen=True)
class TrackingResult:
    frame_index: int
    target_id: str
    bbox: BoundingBox | None
    tracking_status: str
    confidence: float | None = None


@dataclass(slots=True, frozen=True)
class GuidanceResult:
    frame_index: int
    frame_center: Point
    target_center: Point
    dx_pixels: float
    dy_pixels: float
    yaw_offset_deg_approx: float
    pitch_offset_deg_approx: float


@dataclass(slots=True, frozen=True)
class VideoFrame:
    frame_index: int
    timestamp_seconds: float
    frame: object
