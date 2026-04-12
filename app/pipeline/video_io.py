from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import math
from pathlib import Path
import tempfile

import cv2

from app.domain.models import VideoFrame


def should_process_frame(frame_index: int, frame_sampling_interval: int) -> bool:
    if frame_sampling_interval < 1:
        raise ValueError("frame_sampling_interval must be at least 1")
    return frame_index % frame_sampling_interval == 0


def iter_sampled_frame_indices(frame_count: int, frame_sampling_interval: int) -> Iterator[int]:
    if frame_count < 0:
        raise ValueError("frame_count cannot be negative")
    if frame_sampling_interval < 1:
        raise ValueError("frame_sampling_interval must be at least 1")

    for frame_index in range(0, frame_count, frame_sampling_interval):
        yield frame_index


def guess_video_suffix(filename: str | None, mime_type: str | None = None) -> str:
    if filename:
        suffix = Path(filename).suffix
        if suffix:
            return suffix

    if mime_type == "video/quicktime":
        return ".mov"
    if mime_type == "video/x-msvideo":
        return ".avi"
    return ".mp4"


def persist_video_bytes(
    video_bytes: bytes,
    filename: str | None = None,
    mime_type: str | None = None,
) -> str:
    suffix = guess_video_suffix(filename=filename, mime_type=mime_type)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(video_bytes)
        return temp_file.name


def cleanup_persisted_video(path: str | None) -> None:
    if not path:
        return
    Path(path).unlink(missing_ok=True)


def suggest_runtime_detection_interval(
    *,
    source_fps: float,
    requested_interval: int,
    detector_budget_fps: float = 10.0,
) -> int:
    if requested_interval < 1:
        raise ValueError("requested_interval must be at least 1")
    if detector_budget_fps <= 0:
        raise ValueError("detector_budget_fps must be greater than 0")
    if source_fps <= 0:
        return requested_interval
    budget_interval = max(1, math.ceil(source_fps / detector_budget_fps))
    return max(requested_interval, budget_interval)


def suggest_runtime_chunk_size(
    *,
    detection_interval: int,
    detections_per_chunk: int = 4,
) -> int:
    if detection_interval < 1:
        raise ValueError("detection_interval must be at least 1")
    if detections_per_chunk < 1:
        raise ValueError("detections_per_chunk must be at least 1")
    return detection_interval * detections_per_chunk


@contextmanager
def temporary_video_file(
    video_bytes: bytes,
    filename: str | None = None,
    mime_type: str | None = None,
) -> Iterator[str]:
    suffix = guess_video_suffix(filename=filename, mime_type=mime_type)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(video_bytes)
        temp_path = temp_file.name

    try:
        yield temp_path
    finally:
        Path(temp_path).unlink(missing_ok=True)


def iter_sampled_video_frames(
    video_bytes: bytes,
    frame_sampling_interval: int,
    filename: str | None = None,
    mime_type: str | None = None,
) -> Iterator[VideoFrame]:
    if frame_sampling_interval < 1:
        raise ValueError("frame_sampling_interval must be at least 1")

    with temporary_video_file(video_bytes=video_bytes, filename=filename, mime_type=mime_type) as video_path:
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            capture.release()
            raise ValueError("Unable to open uploaded video for frame iteration")

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        fallback_fps = fps if fps > 0 else 30.0

        try:
            frame_index = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break

                if should_process_frame(frame_index=frame_index, frame_sampling_interval=frame_sampling_interval):
                    yield VideoFrame(
                        frame_index=frame_index,
                        timestamp_seconds=frame_index / fallback_fps,
                        frame=frame,
                    )

                frame_index += 1
        finally:
            capture.release()
