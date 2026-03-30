from __future__ import annotations

from app.domain.models import VideoMetadata


def build_placeholder_metadata() -> VideoMetadata:
    fps = 30.0
    frame_count = 180
    return VideoMetadata(
        width=1280,
        height=720,
        fps=fps,
        frame_count=frame_count,
        duration_seconds=frame_count / fps,
    )
