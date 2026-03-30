from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class PipelineEvent:
    stage: str
    message: str
    frame_index: int | None = None
    details: dict[str, str] = field(default_factory=dict)
