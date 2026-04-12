from __future__ import annotations

import cv2

from app.domain.models import VideoMetadata
from app.pipeline.video_io import temporary_video_file


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


def extract_video_metadata(
    video_bytes: bytes,
    filename: str | None = None,
    mime_type: str | None = None,
) -> VideoMetadata:
    with temporary_video_file(video_bytes=video_bytes, filename=filename, mime_type=mime_type) as video_path:
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            capture.release()
            raise ValueError("Unable to open uploaded video for metadata extraction")

        try:
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        finally:
            capture.release()

    safe_fps = fps if fps > 0 else 30.0
    duration_seconds = (frame_count / safe_fps) if frame_count > 0 else 0.0

    return VideoMetadata(
        width=width,
        height=height,
        fps=safe_fps,
        frame_count=frame_count,
        duration_seconds=duration_seconds,
    )
