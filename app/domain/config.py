from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


DEFAULT_HORIZONTAL_FOV_DEG = 78.0
DEFAULT_VERTICAL_FOV_DEG = 49.0


@dataclass(slots=True)
class ProcessingConfig:
    detection_threshold: float = 0.5
    frame_sampling_interval: int = 1
    save_output_video: bool = False
    save_logs: bool = True
    debug_mode: bool = True
    horizontal_fov_deg: float = DEFAULT_HORIZONTAL_FOV_DEG
    vertical_fov_deg: float = DEFAULT_VERTICAL_FOV_DEG
    output_dir: str = "outputs"

    def validate(self) -> None:
        if not 0.0 <= self.detection_threshold <= 1.0:
            raise ValueError("detection_threshold must be between 0.0 and 1.0")
        if self.frame_sampling_interval < 1:
            raise ValueError("frame_sampling_interval must be at least 1")
        if not 0.0 < self.horizontal_fov_deg <= 180.0:
            raise ValueError("horizontal_fov_deg must be between 0.0 and 180.0")
        if not 0.0 < self.vertical_fov_deg <= 180.0:
            raise ValueError("vertical_fov_deg must be between 0.0 and 180.0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
