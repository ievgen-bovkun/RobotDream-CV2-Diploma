from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


DEFAULT_HORIZONTAL_FOV_DEG = 78.0
DEFAULT_VERTICAL_FOV_DEG = 49.0
DEFAULT_CAMERA_PROFILE = "daylight"
DEFAULT_DRONE_PROFILE_ID = "multicopter_center_camera"
DEFAULT_CAMERA_OPTICS_PROFILE_ID = "standard_rectilinear"
DEFAULT_TARGET_PROFILE_ID = "shahed_136"
DEFAULT_DETECTOR_BACKEND = "yolo"
DEFAULT_TARGET_CLASS_MODE = "one_class"
SUPPORTED_CAMERA_PROFILES = ("daylight", "thermal")
SUPPORTED_INPUT_SIZES = {
    "daylight": (768, 960, 1280),
    "thermal": (960, 1280, 1536),
}
SUPPORTED_DETECTOR_BACKENDS = ("yolo", "open_vocab")
SUPPORTED_TARGET_CLASS_MODES = ("one_class",)
CAMERA_PROFILE_PRESETS = {
    "daylight": {
        "input_size": 768,
        "nms_iou_threshold": 0.5,
        "max_detections": 3,
        "prompt_terms": (
            "fixed-wing UAV",
            "flying wing drone",
            "rear view of UAV",
            "top view of UAV",
            "aircraft seen from behind",
        ),
    },
    "thermal": {
        "input_size": 1536,
        "nms_iou_threshold": 0.45,
        "max_detections": 5,
        "prompt_terms": (
            "thermal fixed-wing UAV",
            "thermal drone aircraft",
            "aircraft in thermal camera",
            "low-contrast thermal flying wing",
            "bright aircraft in infrared image",
        ),
    },
}


def get_camera_profile_preset(camera_profile: str) -> dict[str, Any]:
    if camera_profile not in SUPPORTED_CAMERA_PROFILES:
        raise ValueError(f"camera_profile must be one of {SUPPORTED_CAMERA_PROFILES}")
    return CAMERA_PROFILE_PRESETS[camera_profile]


def get_supported_input_sizes(camera_profile: str) -> tuple[int, ...]:
    if camera_profile not in SUPPORTED_CAMERA_PROFILES:
        raise ValueError(f"camera_profile must be one of {SUPPORTED_CAMERA_PROFILES}")
    return SUPPORTED_INPUT_SIZES[camera_profile]


@dataclass(slots=True)
class ProcessingConfig:
    camera_profile: str = DEFAULT_CAMERA_PROFILE
    drone_profile_id: str = DEFAULT_DRONE_PROFILE_ID
    camera_optics_profile_id: str = DEFAULT_CAMERA_OPTICS_PROFILE_ID
    target_profile_id: str = DEFAULT_TARGET_PROFILE_ID
    detection_threshold: float = 0.55
    frame_sampling_interval: int = 3
    tracker_max_missed_refreshes: int = 3
    auto_engagement: bool = False
    engagement_distance_threshold_m: float = 2.0
    save_output_video: bool = False
    save_logs: bool = True
    debug_mode: bool = True
    detector_backend: str = DEFAULT_DETECTOR_BACKEND
    input_size: int | None = None
    nms_iou_threshold: float | None = None
    max_detections: int | None = None
    target_class_mode: str = DEFAULT_TARGET_CLASS_MODE
    prompt_terms: tuple[str, ...] | None = None
    horizontal_fov_deg: float = DEFAULT_HORIZONTAL_FOV_DEG
    vertical_fov_deg: float = DEFAULT_VERTICAL_FOV_DEG
    output_dir: str = "outputs"

    def __post_init__(self) -> None:
        preset = get_camera_profile_preset(self.camera_profile)
        if self.input_size is None:
            self.input_size = int(preset["input_size"])
        if self.nms_iou_threshold is None:
            self.nms_iou_threshold = float(preset["nms_iou_threshold"])
        if self.max_detections is None:
            self.max_detections = int(preset["max_detections"])
        if self.prompt_terms is None:
            self.prompt_terms = tuple(str(term) for term in preset["prompt_terms"])

    def validate(self) -> None:
        if self.camera_profile not in SUPPORTED_CAMERA_PROFILES:
            raise ValueError(f"camera_profile must be one of {SUPPORTED_CAMERA_PROFILES}")
        if not self.drone_profile_id.strip():
            raise ValueError("drone_profile_id must not be blank")
        if not self.camera_optics_profile_id.strip():
            raise ValueError("camera_optics_profile_id must not be blank")
        if not self.target_profile_id.strip():
            raise ValueError("target_profile_id must not be blank")
        if not 0.0 <= self.detection_threshold <= 1.0:
            raise ValueError("detection_threshold must be between 0.0 and 1.0")
        if self.frame_sampling_interval < 1:
            raise ValueError("frame_sampling_interval must be at least 1")
        if self.tracker_max_missed_refreshes < 0:
            raise ValueError("tracker_max_missed_refreshes must be at least 0")
        if self.engagement_distance_threshold_m <= 0.0:
            raise ValueError("engagement_distance_threshold_m must be positive")
        if self.detector_backend not in SUPPORTED_DETECTOR_BACKENDS:
            raise ValueError(
                f"detector_backend must be one of {SUPPORTED_DETECTOR_BACKENDS}"
            )
        if self.input_size < 128:
            raise ValueError("input_size must be at least 128")
        if not 0.0 <= self.nms_iou_threshold <= 1.0:
            raise ValueError("nms_iou_threshold must be between 0.0 and 1.0")
        if self.max_detections < 1:
            raise ValueError("max_detections must be at least 1")
        if self.target_class_mode not in SUPPORTED_TARGET_CLASS_MODES:
            raise ValueError(
                f"target_class_mode must be one of {SUPPORTED_TARGET_CLASS_MODES}"
            )
        if not self.prompt_terms:
            raise ValueError("prompt_terms must contain at least one prompt")
        if any(not term.strip() for term in self.prompt_terms):
            raise ValueError("prompt_terms must not contain blank prompts")
        if not 0.0 < self.horizontal_fov_deg <= 180.0:
            raise ValueError("horizontal_fov_deg must be between 0.0 and 180.0")
        if not 0.0 < self.vertical_fov_deg <= 180.0:
            raise ValueError("vertical_fov_deg must be between 0.0 and 180.0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
