from __future__ import annotations

from typing import Any


def build_log_record(frame_index: int, **payload: Any) -> dict[str, Any]:
    return {
        "frame_index": frame_index,
        **payload,
    }
