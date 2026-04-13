from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Point:
    x: float
    y: float


@dataclass(slots=True, frozen=True)
class DroneProfile:
    profile_id: str
    label: str
    drone_type: str
    camera_offset_x_px: float
    camera_offset_y_px: float
    control_model: str

    def validate(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id must not be blank")
        if self.drone_type not in {"multicopter", "plane"}:
            raise ValueError("drone_type must be either 'multicopter' or 'plane'")
        if self.control_model not in {"motors", "control_surfaces"}:
            raise ValueError(
                "control_model must be either 'motors' or 'control_surfaces'"
            )


@dataclass(slots=True, frozen=True)
class CameraOpticsProfile:
    profile_id: str
    label: str
    lens_model: str
    horizontal_fov_deg: float
    vertical_fov_deg: float
    k1: float = 0.0
    k2: float = 0.0
    p1: float = 0.0
    p2: float = 0.0
    k3: float = 0.0

    def validate(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id must not be blank")
        if self.lens_model not in {"rectilinear", "opencv_radial_tangential"}:
            raise ValueError(
                "lens_model must be either 'rectilinear' or 'opencv_radial_tangential'"
            )
        if not 0.0 < self.horizontal_fov_deg <= 180.0:
            raise ValueError("horizontal_fov_deg must be between 0.0 and 180.0")
        if not 0.0 < self.vertical_fov_deg <= 180.0:
            raise ValueError("vertical_fov_deg must be between 0.0 and 180.0")


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
